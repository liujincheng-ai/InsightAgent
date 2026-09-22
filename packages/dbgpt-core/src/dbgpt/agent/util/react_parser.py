import ast
import json
import re
from dataclasses import dataclass
from html import unescape
from typing import Any, List, Optional

from dbgpt.vis.tags.vis_thinking import VisThinking

# Special tokens leaked as plain text by some model servers (e.g. native
# tool-calling models served behind proxies): ``<|tool_call_end|>``,
# ``<|tool_calls_section_end|>``, ``<|im_end|>`` ... They are inference
# protocol artifacts glued to the real content, never part of it — when
# they stick to an ``Action Input`` JSON tail they break downstream JSON
# parsing and the whole final-answer extraction chain collapses.
_SPECIAL_TOKEN_PATTERN = re.compile(r"<\|[^|<>\n]*\|>")

# Kimi-style native tool-calling protocol leaked as plain text by some model
# servers: ``<|tool_calls_section_begin|><|tool_call_begin|>functions.X:0
# <|tool_call_argument_begin|>{...}<|tool_call_end|><|tool_calls_section_end|>``.
# Native tool-call models intermittently fall back to this protocol instead of
# the textual ReAct format; the argument part has no end marker of its own and
# runs until ``<|tool_call_end|>``. Markers may be space-separated.
_NATIVE_TOOL_CALL_PATTERN = re.compile(
    r"<\|tool_call_begin\|>\s*"
    r"(?:functions\.)?(?P<tool>[\w.\-]+?)\s*(?::\d+)?\s*"
    r"<\|tool_call_argument_begin\|>\s*"
    r"(?P<args>.*?)\s*"
    r"<\|tool_call_end\|>",
    re.DOTALL,
)

# DeepSeek-compatible servers may leak their DSML tool-call envelope as text.
# The full-width vertical bars are intentional (U+FF5C).
_DSML_PREFIX = "<\uff5c\uff5cDSML\uff5c\uff5c"
_DSML_INVOKE_PATTERN = re.compile(
    rf"{re.escape(_DSML_PREFIX)}invoke\s+name=[\"'](?P<tool>[\w.\-]+)[\"']>"
    rf"(?P<body>.*?){re.escape(_DSML_PREFIX)}/invoke>",
    re.DOTALL,
)
_DSML_PARAMETER_PATTERN = re.compile(
    rf"{re.escape(_DSML_PREFIX)}parameter\s+name=[\"'](?P<name>[\w.\-]+)[\"']"
    rf"[^>]*>(?P<value>.*?){re.escape(_DSML_PREFIX)}parameter>",
    re.DOTALL,
)


@dataclass
class ReActStep:
    """
    Dataclass representing a single step in the ReAct pattern.
    """

    thought: Optional[str] = None
    phase: Optional[str] = None
    action_intention: Optional[str] = None
    action_reason: Optional[str] = None
    action: Optional[str] = None
    action_input: Optional[Any] = None
    observation: Optional[Any] = None
    is_terminal: bool = False


class ReActOutputParser:
    """
    Parser for ReAct format model outputs with configurable prefixes.
    This parser extracts structured information from language model outputs
    that follow the ReAct pattern: Thought -> Phase -> Action -> Action Input
    -> Observation.
    """

    def __init__(
        self,
        thought_prefix: str = "Thought:",
        phase_prefix: str = "Phase:",
        action_intention_prefix: str = "Action Intention:",
        action_reason_prefix: str = "Action Reason:",
        action_prefix: str = "Action:",
        action_input_prefix: str = "Action Input:",
        observation_prefix: str = "Observation:",
        terminate_action: str = "terminate",
    ):
        """
        Initialize the ReAct output parser with configurable prefixes.

        Args:
            thought_prefix: Prefix string that indicates the start of a thought.
            phase_prefix: Prefix string that indicates the start of a phase.
            action_intention_prefix: Prefix string that indicates the start of
                an action intention.
            action_reason_prefix: Prefix string that indicates the start of an
                action reason.
            action_prefix: Prefix string that indicates the start of an action.
            action_input_prefix: Prefix string that indicates the start of action input.
            observation_prefix: Prefix string that indicates the start of an
                observation.
            terminate_action: String that indicates termination action.
        """
        self.thought_prefix = thought_prefix
        self.phase_prefix = phase_prefix
        self.action_intention_prefix = action_intention_prefix
        self.action_reason_prefix = action_reason_prefix
        self.action_prefix = action_prefix
        self.action_input_prefix = action_input_prefix
        self.observation_prefix = observation_prefix
        self.terminate_action = terminate_action

        # Escape special regex characters in prefixes
        self.thought_prefix_escaped = re.escape(thought_prefix)
        self.phase_prefix_escaped = re.escape(phase_prefix)
        self.action_intention_prefix_escaped = re.escape(action_intention_prefix)
        self.action_reason_prefix_escaped = re.escape(action_reason_prefix)
        self.action_prefix_escaped = re.escape(action_prefix)
        self.action_input_prefix_escaped = re.escape(action_input_prefix)
        self.observation_prefix_escaped = re.escape(observation_prefix)

    def _prefix_line_pattern(self, escaped_prefix: str) -> str:
        """Build a regex for a ReAct prefix at the start of a logical line."""
        return rf"^[ \t]*{escaped_prefix}\s*"

    def _markdown_fence_spans(self, text: str) -> List[tuple[int, int]]:
        """Return markdown fenced-code spans so ReAct labels inside are ignored."""
        fence_pattern = re.compile(
            r"^[ \t]*(```+|~~~+)[^\n]*\n.*?^[ \t]*\1[ \t]*$",
            re.DOTALL | re.MULTILINE,
        )
        return [match.span() for match in fence_pattern.finditer(text)]

    @staticmethod
    def _is_in_spans(pos: int, spans: List[tuple[int, int]]) -> bool:
        return any(start <= pos < end for start, end in spans)

    def _find_prefix_matches(self, text: str, escaped_prefix: str) -> List[re.Match]:
        """Find line-start ReAct prefix matches outside markdown code fences."""
        pattern = re.compile(self._prefix_line_pattern(escaped_prefix), re.MULTILINE)
        fence_spans = self._markdown_fence_spans(text)
        return [
            match
            for match in pattern.finditer(text)
            if not self._is_in_spans(match.start(), fence_spans)
        ]

    def _mask_prefixes_in_fences(self, text: str) -> str:
        """Mask ReAct labels inside code fences while preserving string offsets."""
        chars = list(text)
        escaped_prefixes = (
            self.thought_prefix_escaped,
            self.phase_prefix_escaped,
            self.action_intention_prefix_escaped,
            self.action_reason_prefix_escaped,
            self.action_prefix_escaped,
            self.action_input_prefix_escaped,
            self.observation_prefix_escaped,
        )
        for start, end in self._markdown_fence_spans(text):
            fenced_text = text[start:end]
            for escaped_prefix in escaped_prefixes:
                pattern = re.compile(
                    self._prefix_line_pattern(escaped_prefix), re.MULTILINE
                )
                for match in pattern.finditer(fenced_text):
                    prefix_start = start + match.start()
                    while prefix_start < end and chars[prefix_start] in (" ", "\t"):
                        prefix_start += 1
                    if prefix_start < end:
                        chars[prefix_start] = "_"
        return "".join(chars)

    def _strip_vis_thinking_blocks(self, text: str) -> str:
        """Remove vis-thinking wrappers produced by reasoning model output."""
        fence = "`" * 6
        pattern = (
            rf"{re.escape(fence)}{re.escape(VisThinking.vis_tag())}"
            rf"\s*\n.*?\n{re.escape(fence)}\s*"
        )
        return re.sub(pattern, "", text, flags=re.DOTALL)

    def _strip_markdown_code_fence(self, text: str) -> str:
        """Remove a markdown fence that wraps the whole ReAct response."""
        stripped = text.strip()
        match = re.fullmatch(r"```[a-zA-Z0-9_-]*\s*\n(.*?)\n```", stripped, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text

    def _normalize_markdown_protocol_markers(self, text: str) -> str:
        """Turn Markdown-rendered ReAct labels into plain protocol labels.

        Some chat models emit ``## Action:`` or ``**Action:**`` despite the
        plain-text format requested by the agent prompt.  Internal fenced code
        is deliberately left untouched because those labels can be examples or
        file content rather than actual ReAct steps.
        """
        marker_names = (
            "Thought|Phase|Action Intention|Action Reason|Action Input|"
            "Action|Observation"
        )

        def _replace_outside_fences(pattern: str, value: str) -> None:
            nonlocal text
            fence_spans = self._markdown_fence_spans(text)

            def _replace(match: "re.Match[str]") -> str:
                if self._is_in_spans(match.start(), fence_spans):
                    return match.group(0)
                return match.expand(value)

            text = re.sub(pattern, _replace, text)

        _replace_outside_fences(
            rf"(?m)^[ \t]*#{{1,6}}[ \t]+({marker_names}):[ \t]*",
            r"\1: ",
        )
        _replace_outside_fences(
            rf"(?m)^[ \t]*\*\*({marker_names}):\*\*[ \t]*",
            r"\1: ",
        )
        # Streaming adapters can prepend ``Thought:`` to content that already
        # starts with its own Markdown Thought heading.
        _replace_outside_fences(
            r"(?m)^Thought:\s*(?:#{1,6}\s*)Thought:\s*",
            "Thought: ",
        )
        return text

    def _normalize_protocol_punctuation(self, text: str) -> str:
        """Normalize full-width colons and inline ReAct labels.

        Reasoning models sometimes keep the requested labels but render them on
        one line or use the Chinese full-width colon.  Both forms still carry an
        explicit tool choice, so translating them to the canonical line-based
        protocol is lossless.
        """

        marker_names = (
            "Thought|Phase|Action Intention|Action Reason|Action Input|"
            "Action|Observation"
        )
        fence_spans = self._markdown_fence_spans(text)
        chunks: List[str] = []
        cursor = 0
        for start, end in fence_spans:
            chunks.append(
                self._normalize_protocol_chunk(text[cursor:start], marker_names)
            )
            chunks.append(text[start:end])
            cursor = end
        chunks.append(self._normalize_protocol_chunk(text[cursor:], marker_names))
        return "".join(chunks)

    @staticmethod
    def _normalize_protocol_chunk(text: str, marker_names: str) -> str:
        text = re.sub(rf"({marker_names})\s*：\s*", r"\1: ", text)
        if "Action:" not in text or "Action Input:" not in text:
            return text
        return re.sub(
            r"(?<!\n)[ \t]+(Action Input|Action):[ \t]*",
            r"\n\1: ",
            text,
        )

    @staticmethod
    def _mapping_candidates(text: str) -> List[tuple[int, int, dict[str, Any]]]:
        """Return JSON/Python-literal mapping candidates embedded in output."""

        candidates: List[tuple[int, int, dict[str, Any]]] = []
        decoder = json.JSONDecoder()
        for start, char in enumerate(text):
            if char != "{":
                continue
            try:
                value, consumed = decoder.raw_decode(text[start:])
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
            if isinstance(value, dict):
                candidates.append((start, start + consumed, value))

        stripped = text.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                value = ast.literal_eval(stripped)
            except (SyntaxError, ValueError, TypeError):
                value = None
            if isinstance(value, dict) and not any(
                item[2] == value for item in candidates
            ):
                start = text.find(stripped)
                candidates.append((start, start + len(stripped), value))
        return candidates

    @staticmethod
    def _structured_value(payload: dict[str, Any], *names: str) -> Any:
        normalized = {
            str(key).strip().lower().replace("_", " "): value
            for key, value in payload.items()
        }
        for name in names:
            if name in normalized:
                return normalized[name]
        return None

    def _parse_structured_step(self, text: str) -> Optional[ReActStep]:
        """Parse explicit JSON ReAct envelopes without guessing tool intent."""

        for start, _end, payload in self._mapping_candidates(text):
            action = self._structured_value(payload, "action", "tool", "tool name")
            action_input = self._structured_value(
                payload,
                "action input",
                "arguments",
                "parameters",
                "input",
            )
            thought = self._structured_value(payload, "thought", "reasoning")
            if isinstance(action, str) and action.strip() and action_input is not None:
                return ReActStep(
                    thought=(str(thought).strip() if thought is not None else None),
                    action=action.strip(),
                    action_input=action_input,
                    is_terminal=action.strip().lower() == self.terminate_action.lower(),
                )

            # Exact shapes are unambiguous protocol shorthands already used by
            # several model servers.  No business Tool is inferred here.
            if set(payload) == {"sql"} and isinstance(payload["sql"], str):
                sql = payload["sql"].strip()
                if sql:
                    return ReActStep(
                        thought="执行模型提供的严格 JSON SQL 查询。",
                        action="sql_query",
                        action_input={"sql": sql},
                    )
            if set(payload) in ({"output"}, {"result"}):
                key = next(iter(payload))
                if isinstance(payload[key], str):
                    return ReActStep(
                        thought="返回模型提供的最终答案。",
                        action=self.terminate_action,
                        action_input={key: payload[key]},
                        is_terminal=True,
                    )

            # Preserve a useful prose Thought when an explicit JSON envelope is
            # appended after it but omits the optional Thought member.
            if isinstance(action, str) and action.strip():
                prefix = text[:start].strip()
                if prefix.startswith(self.thought_prefix):
                    thought = prefix[len(self.thought_prefix) :].strip() or None
                return ReActStep(
                    thought=thought,
                    action=action.strip(),
                    action_input=action_input,
                    is_terminal=action.strip().lower() == self.terminate_action.lower(),
                )
        return None

    def format_error_message(self, text: str) -> str:
        """Return actionable retry feedback for malformed model protocol."""

        if self._mapping_candidates(self._normalize_react_text(text)):
            return (
                "A JSON/Python argument object was detected, but no executable Action "
                "was found. Do not output arguments alone. Repeat the same decision "
                "with an explicit tool name, for example: Action: <tool_name> followed "
                "by Action Input: <JSON object>; or use one JSON object with keys "
                '"Action" and "Action Input".'
            )
        return (
            "No executable Action was found. Output exactly one explicit Action and "
            "one Action Input in the format required by the system prompt."
        )

    def _translate_native_tool_calls(self, text: str) -> str:
        """Translate leaked native tool-call blocks into ReAct text lines.

        Runs BEFORE the special-token stripping so the tool name and JSON
        arguments survive; leftover section wrapper markers are removed by
        the token pass in :meth:`_normalize_react_text`. Free text around
        the call is preserved — the ``Action:``-split fallback in
        :meth:`parse` handles blocks without a ``Thought:`` prefix.
        """
        if "<|tool_call_begin|>" not in text and _DSML_PREFIX not in text:
            return text

        def _render_dsml(match: "re.Match[str]") -> str:
            arguments: dict[str, str] = {}
            for parameter in _DSML_PARAMETER_PATTERN.finditer(match.group("body")):
                arguments[parameter.group("name")] = unescape(
                    parameter.group("value").strip()
                )
            return (
                f"\nAction: {match.group('tool')}\n"
                f"Action Input: {json.dumps(arguments, ensure_ascii=False)}\n"
            )

        text = _DSML_INVOKE_PATTERN.sub(_render_dsml, text)
        text = re.sub(
            rf"{re.escape(_DSML_PREFIX)}(?:tool_calls>|/tool_calls>)", "", text
        )

        def _render(match: "re.Match[str]") -> str:
            tool = match.group("tool")
            args = match.group("args").strip()
            return f"\nAction: {tool}\nAction Input: {args}\n"

        return _NATIVE_TOOL_CALL_PATTERN.sub(_render, text)

    def _normalize_react_text(self, text: str) -> str:
        """Normalize common wrappers before ReAct parsing."""
        if not text:
            return text

        text = self._translate_native_tool_calls(text)
        text = _SPECIAL_TOKEN_PATTERN.sub("", text)
        text = self._strip_vis_thinking_blocks(text)
        text = self._strip_markdown_code_fence(text)
        text = self._normalize_markdown_protocol_markers(text)
        text = self._normalize_protocol_punctuation(text)
        stripped = text.lstrip()
        fence = "`" * 6
        opening = f"{fence}{VisThinking.vis_tag()}"
        if not stripped.startswith(opening):
            return text

        lines = stripped.splitlines()
        if len(lines) < 3 or lines[0].strip() != opening:
            return text

        closing_index = None
        for idx in range(1, len(lines)):
            if lines[idx].strip() == fence:
                trailing_content = "\n".join(lines[idx + 1 :]).lstrip()
                if not trailing_content or trailing_content.startswith(
                    self.thought_prefix
                ):
                    closing_index = idx
                    break

        if closing_index is None:
            return text

        return "\n".join(lines[closing_index + 1 :]).lstrip()

    def parse(self, text: str) -> List[ReActStep]:
        """
        Parse the ReAct format output text into structured steps.

        Args:
            text: The text to parse, containing ReAct formatted content.

        Returns:
            List of ReActStep dataclasses, each containing thought, action,
                action_input, and observation.
        """
        # Split the text into steps based on thought prefix
        steps = []

        # Remove any leading/trailing whitespace
        text = self._normalize_react_text(text).strip()

        # Canonical line-based ReAct remains the source of truth, especially
        # for multi-step history containing nested SQL/output objects.  The
        # structured fallback is only needed when one of those explicit lines
        # is missing.
        has_action_line = bool(
            self._find_prefix_matches(text, self.action_prefix_escaped)
        )
        has_action_input_line = bool(
            self._find_prefix_matches(text, self.action_input_prefix_escaped)
        )
        if not (has_action_line and has_action_input_line):
            structured_step = self._parse_structured_step(text)
            if structured_step is not None:
                return [structured_step]

        # Find all line-start instances of the thought prefix outside code fences.
        thought_matches = self._find_prefix_matches(text, self.thought_prefix_escaped)

        if not thought_matches:
            # Fallback: if no Thought: prefix found, try splitting on
            # Action: prefix so we can still parse responses that omit
            # Thought:.  Each step starts from the text before Action: (to
            # capture Action Intention / Action Reason) up to the next
            # Action: or end of text.
            action_matches = self._find_prefix_matches(text, self.action_prefix_escaped)
            if not action_matches:
                return []
            steps = []
            for i, match in enumerate(action_matches):
                # Include text before the Action: prefix (may contain
                # Action Intention / Action Reason lines).
                # Walk backwards to find the start of this logical block.
                if i == 0:
                    start_pos = 0
                else:
                    start_pos = action_matches[i - 1].end()
                end_pos = (
                    action_matches[i + 1].start()
                    if i < len(action_matches) - 1
                    else len(text)
                )
                step_text = text[start_pos:end_pos].strip()
                step_data = self._parse_step(step_text)
                if step_data:
                    steps.append(step_data)
            return steps

        # Process each thought section
        for i, match in enumerate(thought_matches):
            start_pos = match.start()

            # Determine end position (either next thought or end of text)
            if i < len(thought_matches) - 1:
                end_pos = thought_matches[i + 1].start()
            else:
                end_pos = len(text)

            # Extract the current step's text
            step_text = text[start_pos:end_pos].strip()

            # Parse the step
            step_data = self._parse_step(step_text)
            if step_data:
                steps.append(step_data)

        return steps

    def parse_current_step(self, text: str) -> List[ReActStep]:
        """Parse the single step that should be executed in the current round.

        Some reasoning models incorrectly emit a whole ReAct trajectory in one
        response. InsightAgent executes one action per round, so callers that are about
        to run tools should use only the first actionable step while preserving
        ``parse()`` for history and diagnostics.
        """
        steps = self.parse(text)
        if len(steps) <= 1:
            return steps
        for step in steps:
            if step.action:
                return [step]
        return [steps[0]]

    def _parse_step(self, step_text: str) -> Optional[ReActStep]:
        """
        Parse a single step of the ReAct format.

        Args:
            step_text: Text containing a single thought-action-input-observation
                sequence.

        Returns:
            ReActStep dataclass with thought, action, action_input, and observation,
                or None if parsing fails.
        """
        # Initialize the result
        thought = None
        phase = None
        action_intention = None
        action_reason = None
        action = None
        action_input = None
        observation = None
        is_terminal = False
        match_text = self._mask_prefixes_in_fences(step_text)

        # Extract thought
        thought_line = self._prefix_line_pattern(self.thought_prefix_escaped)
        phase_line = self._prefix_line_pattern(self.phase_prefix_escaped)
        action_intention_line = self._prefix_line_pattern(
            self.action_intention_prefix_escaped
        )
        action_reason_line = self._prefix_line_pattern(
            self.action_reason_prefix_escaped
        )
        action_line = self._prefix_line_pattern(self.action_prefix_escaped)
        action_input_line = self._prefix_line_pattern(self.action_input_prefix_escaped)
        observation_line = self._prefix_line_pattern(self.observation_prefix_escaped)

        thought_match = re.search(
            rf"{thought_line}(.*?)(?={phase_line}|{action_intention_line}|"
            rf"{action_reason_line}|{action_line}|{observation_line}|\Z)",
            match_text,
            re.DOTALL | re.MULTILINE,
        )
        if thought_match:
            thought = step_text[thought_match.start(1) : thought_match.end(1)].strip()

        # Extract phase (optional, between thought and action)
        phase_match = re.search(
            rf"{phase_line}(.*?)(?={action_intention_line}|{action_reason_line}|"
            rf"{action_line}|{action_input_line}|{observation_line}|\Z)",
            match_text,
            re.DOTALL | re.MULTILINE,
        )
        if phase_match:
            phase = step_text[phase_match.start(1) : phase_match.end(1)].strip() or None

        # Extract action intention (optional, short user-facing intent)
        action_intention_match = re.search(
            rf"{action_intention_line}(.*?)(?={action_reason_line}|{action_line}|"
            rf"{action_input_line}|{observation_line}|\Z)",
            match_text,
            re.DOTALL | re.MULTILINE,
        )
        if action_intention_match:
            action_intention = (
                step_text[
                    action_intention_match.start(1) : action_intention_match.end(1)
                ].strip()
                or None
            )

        # Extract action reason (optional, short user-facing reason)
        action_reason_match = re.search(
            rf"{action_reason_line}(.*?)(?={action_intention_line}|{action_line}|"
            rf"{action_input_line}|{observation_line}|\Z)",
            match_text,
            re.DOTALL | re.MULTILINE,
        )
        if action_reason_match:
            action_reason = (
                step_text[
                    action_reason_match.start(1) : action_reason_match.end(1)
                ].strip()
                or None
            )

        # Extract action
        action_match = re.search(
            rf"{action_line}(.*?)(?={action_input_line}|{observation_line}|\Z)",
            match_text,
            re.DOTALL | re.MULTILINE,
        )
        if action_match:
            action = step_text[action_match.start(1) : action_match.end(1)].strip()

            # Check if this is a terminate action
            is_terminal = action.lower() == self.terminate_action.lower()

        # Extract action input
        action_input_match = re.search(
            rf"{action_input_line}(.*?)(?={observation_line}|{thought_line}|\Z)",
            match_text,
            re.DOTALL | re.MULTILINE,
        )
        if action_input_match:
            action_input_text = step_text[
                action_input_match.start(1) : action_input_match.end(1)
            ].strip()

            # Try to parse action input as JSON if it looks like JSON
            if (
                action_input_text.startswith("{") and action_input_text.endswith("}")
            ) or (
                action_input_text.startswith("[") and action_input_text.endswith("]")
            ):
                try:
                    action_input = json.loads(action_input_text)
                except json.JSONDecodeError:
                    action_input = action_input_text
            else:
                action_input = action_input_text

        # A small set of chat models occasionally places an otherwise valid
        # sql_query payload directly after ``Thought:`` and omits both action
        # labels.  Recover only the exact, strict SQL object shape; malformed
        # JSON, extra keys, and prose remain rejected by the normal parser.
        if action is None and action_input is None and thought:
            try:
                thought_payload = json.loads(thought)
            except (json.JSONDecodeError, TypeError):
                thought_payload = None
            if (
                isinstance(thought_payload, dict)
                and set(thought_payload) == {"sql"}
                and isinstance(thought_payload["sql"], str)
                and thought_payload["sql"].strip()
            ):
                action = "sql_query"
                action_input = {"sql": thought_payload["sql"].strip()}
                thought = "执行模型提供的严格 JSON SQL 查询。"

        # Extract observation
        observation_match = re.search(
            rf"{observation_line}(.*?)(?={thought_line}|\Z)",
            match_text,
            re.DOTALL | re.MULTILINE,
        )
        if observation_match:
            observation_text = step_text[
                observation_match.start(1) : observation_match.end(1)
            ].strip()

            # Try to parse observation as JSON if it looks like JSON
            if (
                observation_text.startswith("{") and observation_text.endswith("}")
            ) or (observation_text.startswith("[") and observation_text.endswith("]")):
                try:
                    observation = json.loads(observation_text)
                except json.JSONDecodeError:
                    observation = observation_text
            else:
                observation = observation_text

        # Only return if we have at least thought or action
        if thought or action:
            return ReActStep(
                thought=thought,
                phase=phase,
                action_intention=action_intention,
                action_reason=action_reason,
                action=action,
                action_input=action_input,
                observation=observation,
                is_terminal=is_terminal,
            )
        return None

    def get_final_output(self, steps: List[ReActStep]) -> Optional[str]:
        """
        Get the final output from a terminate action if it exists.

        Args:
            steps: List of parsed steps.

        Returns:
            The final output string or None if no terminate action is found.
        """
        for step in reversed(steps):  # Look from the end
            if step.is_terminal and step.action == self.terminate_action:
                if (
                    isinstance(step.action_input, dict)
                    and "result" in step.action_input
                ):
                    return step.action_input["result"]
                if (
                    isinstance(step.action_input, dict)
                    and "output" in step.action_input
                ):
                    return step.action_input["output"]
        return None
