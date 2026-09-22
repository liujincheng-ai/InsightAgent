import { CloseOutlined, LoadingOutlined, PaperClipOutlined, SendOutlined } from '@ant-design/icons';
import { Button, Spin } from 'antd';
import classNames from 'classnames';
import React, { forwardRef, useCallback, useImperativeHandle, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import CommandPopover, { SlashCommand } from './CommandPopover';
import MentionPopover, { MentionOption } from './MentionPopover';
import { useFilteredList } from './hooks/useFilteredList';

export interface ContentPart {
  type: 'text' | 'file' | 'agent' | 'image';
  content: string;
  path?: string;
  name?: string;
  dataUrl?: string;
  filename?: string;
}

export interface EnhancedChatInputRef {
  focus: () => void;
  clear: () => void;
  getValue: () => string;
  setValue: (value: string) => void;
  getParts: () => ContentPart[];
}

interface EnhancedChatInputProps {
  onSubmit: (text: string, parts: ContentPart[]) => void;
  disabled?: boolean;
  loading?: boolean;
  placeholder?: string;
  agents?: Array<{ name: string; description?: string }>;
  commands?: SlashCommand[];
  onFileSearch?: (query: string) => Promise<string[]>;
  onCommandSelect?: (command: SlashCommand) => void;
  className?: string;
  maxHeight?: number;
}

const ACCEPTED_IMAGE_TYPES = ['image/png', 'image/jpeg', 'image/gif', 'image/webp'];

const EnhancedChatInput = forwardRef<EnhancedChatInputRef, EnhancedChatInputProps>(
  (
    {
      onSubmit,
      disabled = false,
      loading = false,
      placeholder,
      agents = [],
      commands = [],
      onFileSearch,
      onCommandSelect,
      className,
      maxHeight = 200,
    },
    ref,
  ) => {
    const { t } = useTranslation();
    const editorRef = useRef<HTMLDivElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    const [isFocused, setIsFocused] = useState(false);
    const [isComposing, setIsComposing] = useState(false);
    const [popoverType, setPopoverType] = useState<'at' | 'slash' | null>(null);
    const [imageAttachments, setImageAttachments] = useState<ContentPart[]>([]);
    const [history, setHistory] = useState<string[]>([]);
    const [historyIndex, setHistoryIndex] = useState(-1);
    const [savedInput, setSavedInput] = useState<string | null>(null);

    const agentOptions: MentionOption[] = useMemo(
      () => agents.map(a => ({ type: 'agent', name: a.name, display: a.name, description: a.description })),
      [agents],
    );

    const fetchMentionOptions = useCallback(
      async (query: string): Promise<MentionOption[]> => {
        const fileOptions: MentionOption[] = [];

        if (onFileSearch) {
          try {
            const files = await onFileSearch(query);
            files.forEach(path => {
              const isDirectory = path.endsWith('/');
              fileOptions.push({ type: 'file', path, display: path, isDirectory });
            });
          } catch (error) {
            console.error('File search error:', error);
          }
        }

        return [...agentOptions, ...fileOptions];
      },
      [agentOptions, onFileSearch],
    );

    const handleMentionSelect = useCallback((option: MentionOption | undefined) => {
      if (!option || !editorRef.current) return;

      const selection = window.getSelection();
      if (!selection || selection.rangeCount === 0) return;

      const range = selection.getRangeAt(0);
      const textNode = range.startContainer;

      if (textNode.nodeType === Node.TEXT_NODE) {
        const text = textNode.textContent || '';
        const cursorPos = range.startOffset;
        const atIndex = text.lastIndexOf('@', cursorPos - 1);

        if (atIndex >= 0) {
          const beforeAt = text.substring(0, atIndex);
          const afterCursor = text.substring(cursorPos);

          const pill = createPill(option);
          const beforeNode = document.createTextNode(beforeAt);
          const afterNode = document.createTextNode(' ' + afterCursor);

          const parent = textNode.parentNode;
          if (parent) {
            parent.insertBefore(beforeNode, textNode);
            parent.insertBefore(pill, textNode);
            parent.insertBefore(afterNode, textNode);
            parent.removeChild(textNode);

            const newRange = document.createRange();
            newRange.setStart(afterNode, 1);
            newRange.collapse(true);
            selection.removeAllRanges();
            selection.addRange(newRange);
          }
        }
      }

      setPopoverType(null);
    }, []);

    const {
      flat: mentionFlat,
      active: mentionActive,
      onInput: mentionOnInput,
      onKeyDown: mentionOnKeyDown,
      loading: mentionLoading,
    } = useFilteredList<MentionOption>({
      items: fetchMentionOptions,
      key: opt => (opt ? (opt.type === 'agent' ? `agent:${opt.name}` : `file:${opt.path}`) : ''),
      filterKeys: ['display'],
      onSelect: handleMentionSelect,
    });

    const handleCommandSelect = useCallback(
      (command: SlashCommand | undefined) => {
        if (!command || !editorRef.current) return;

        if (onCommandSelect) {
          onCommandSelect(command);
        }

        editorRef.current.innerHTML = '';
        if (command.type === 'custom') {
          editorRef.current.textContent = `/${command.trigger} `;
          setCursorToEnd(editorRef.current);
        }

        setPopoverType(null);
      },
      [onCommandSelect],
    );

    const {
      flat: commandFlat,
      active: commandActive,
      onInput: commandOnInput,
      onKeyDown: commandOnKeyDown,
      loading: commandLoading,
    } = useFilteredList<SlashCommand>({
      items: commands,
      key: cmd => cmd?.id ?? '',
      filterKeys: ['trigger', 'title', 'description'],
      onSelect: handleCommandSelect,
    });

    const createPill = (option: MentionOption): HTMLSpanElement => {
      const pill = document.createElement('span');
      pill.textContent = '@' + option.display;
      pill.setAttribute('data-type', option.type);
      if (option.type === 'file') pill.setAttribute('data-path', option.path);
      if (option.type === 'agent') pill.setAttribute('data-name', option.name);
      pill.setAttribute('contenteditable', 'false');
      pill.className =
        'inline-flex items-center px-1.5 py-0.5 mx-0.5 rounded bg-blue-100 text-blue-700 text-sm cursor-default dark:bg-blue-900/30 dark:text-blue-300';
      pill.style.userSelect = 'text';
      return pill;
    };

    const setCursorToEnd = (element: HTMLElement) => {
      const range = document.createRange();
      const selection = window.getSelection();
      range.selectNodeContents(element);
      range.collapse(false);
      selection?.removeAllRanges();
      selection?.addRange(range);
    };

    const getTextContent = (): string => {
      if (!editorRef.current) return '';
      return editorRef.current.innerText || '';
    };

    const parseContentParts = (): ContentPart[] => {
      if (!editorRef.current) return [];

      const parts: ContentPart[] = [];
      let textBuffer = '';

      const flushText = () => {
        const content = textBuffer.replace(/\r\n?/g, '\n').trim();
        textBuffer = '';
        if (content) {
          parts.push({ type: 'text', content });
        }
      };

      const visit = (node: Node) => {
        if (node.nodeType === Node.TEXT_NODE) {
          textBuffer += node.textContent || '';
          return;
        }

        if (node.nodeType === Node.ELEMENT_NODE) {
          const el = node as HTMLElement;

          if (el.dataset.type === 'file') {
            flushText();
            parts.push({ type: 'file', content: el.textContent || '', path: el.dataset.path });
            return;
          }

          if (el.dataset.type === 'agent') {
            flushText();
            parts.push({ type: 'agent', content: el.textContent || '', name: el.dataset.name });
            return;
          }

          if (el.tagName === 'BR') {
            textBuffer += '\n';
            return;
          }

          Array.from(el.childNodes).forEach(visit);
        }
      };

      Array.from(editorRef.current.childNodes).forEach(visit);
      flushText();

      return [...parts, ...imageAttachments];
    };

    const handleInput = () => {
      if (!editorRef.current) return;

      const text = getTextContent();
      const selection = window.getSelection();
      if (!selection || selection.rangeCount === 0) return;

      const range = selection.getRangeAt(0);
      const textNode = range.startContainer;

      if (textNode.nodeType === Node.TEXT_NODE) {
        const nodeText = textNode.textContent || '';
        const cursorPos = range.startOffset;
        const textBeforeCursor = nodeText.substring(0, cursorPos);

        const atMatch = textBeforeCursor.match(/@(\S*)$/);
        if (atMatch) {
          setPopoverType('at');
          mentionOnInput(atMatch[1]);
          return;
        }

        if (text.startsWith('/') && !text.includes(' ')) {
          setPopoverType('slash');
          commandOnInput(text.substring(1));
          return;
        }
      }

      setPopoverType(null);
    };

    const handleKeyDown = (event: React.KeyboardEvent) => {
      if (isComposing) return;

      if (popoverType === 'at') {
        if (mentionOnKeyDown(event)) return;
      }

      if (popoverType === 'slash') {
        if (commandOnKeyDown(event)) return;
      }

      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        handleSubmit();
        return;
      }

      if (event.key === 'ArrowUp' && !popoverType) {
        const text = getTextContent();
        if (!text && history.length > 0) {
          event.preventDefault();
          if (historyIndex === -1) {
            setSavedInput(text);
          }
          const newIndex = Math.min(historyIndex + 1, history.length - 1);
          setHistoryIndex(newIndex);
          if (editorRef.current) {
            editorRef.current.textContent = history[newIndex];
            setCursorToEnd(editorRef.current);
          }
          return;
        }
      }

      if (event.key === 'ArrowDown' && !popoverType) {
        if (historyIndex >= 0) {
          event.preventDefault();
          const newIndex = historyIndex - 1;
          setHistoryIndex(newIndex);
          if (editorRef.current) {
            if (newIndex < 0) {
              editorRef.current.textContent = savedInput || '';
            } else {
              editorRef.current.textContent = history[newIndex];
            }
            setCursorToEnd(editorRef.current);
          }
          return;
        }
      }

      if (event.key === 'Escape') {
        if (popoverType) {
          event.preventDefault();
          setPopoverType(null);
        }
      }
    };

    const handleSubmit = () => {
      if (disabled || loading) return;

      const text = getTextContent().trim();
      const parts = parseContentParts();

      if (!text && imageAttachments.length === 0) return;

      if (text) {
        setHistory(prev => [text, ...prev.slice(0, 99)]);
      }

      onSubmit(text, parts);

      if (editorRef.current) {
        editorRef.current.innerHTML = '';
      }
      setImageAttachments([]);
      setHistoryIndex(-1);
      setSavedInput(null);
    };

    const handlePaste = async (event: React.ClipboardEvent) => {
      const clipboardData = event.clipboardData;
      if (!clipboardData) return;

      const items = Array.from(clipboardData.items);
      const imageItems = items.filter(item => item.kind === 'file' && ACCEPTED_IMAGE_TYPES.includes(item.type));

      if (imageItems.length > 0) {
        event.preventDefault();
        for (const item of imageItems) {
          const file = item.getAsFile();
          if (file) await addImageAttachment(file);
        }
        return;
      }
    };

    const handleDrop = async (event: React.DragEvent) => {
      event.preventDefault();
      const files = event.dataTransfer?.files;
      if (!files) return;

      for (const file of Array.from(files)) {
        if (ACCEPTED_IMAGE_TYPES.includes(file.type)) {
          await addImageAttachment(file);
        }
      }
    };

    const addImageAttachment = async (file: File) => {
      return new Promise<void>(resolve => {
        const reader = new FileReader();
        reader.onload = () => {
          const dataUrl = reader.result as string;
          setImageAttachments(prev => [
            ...prev,
            {
              type: 'image',
              content: '',
              dataUrl,
              filename: file.name,
            },
          ]);
          resolve();
        };
        reader.readAsDataURL(file);
      });
    };

    const removeImageAttachment = (index: number) => {
      setImageAttachments(prev => prev.filter((_, i) => i !== index));
    };

    const handleFileInputChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
      const files = event.target.files;
      if (!files) return;

      for (const file of Array.from(files)) {
        if (ACCEPTED_IMAGE_TYPES.includes(file.type)) {
          await addImageAttachment(file);
        }
      }
      event.target.value = '';
    };

    useImperativeHandle(ref, () => ({
      focus: () => editorRef.current?.focus(),
      clear: () => {
        if (editorRef.current) {
          editorRef.current.innerHTML = '';
        }
        setImageAttachments([]);
      },
      getValue: getTextContent,
      setValue: (value: string) => {
        if (editorRef.current) {
          editorRef.current.textContent = value;
          setCursorToEnd(editorRef.current);
        }
      },
      getParts: parseContentParts,
    }));

    const hasContent = getTextContent().trim() || imageAttachments.length > 0;

    return (
      <div
        ref={containerRef}
        className={classNames(
          'relative flex flex-col rounded-xl border bg-white transition-colors dark:bg-[rgba(255,255,255,0.08)]',
          isFocused ? 'border-blue-500 dark:border-blue-400' : 'border-gray-200 dark:border-gray-700',
          className,
        )}
      >
        {imageAttachments.length > 0 && (
          <div className='flex flex-wrap gap-2 p-3 pb-0'>
            {imageAttachments.map((img, index) => (
              <div key={index} className='group relative'>
                <img src={img.dataUrl} alt={img.filename} className='h-16 w-16 rounded-lg object-cover' />
                <button
                  type='button'
                  onClick={() => removeImageAttachment(index)}
                  className='absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-white opacity-0 transition-opacity group-hover:opacity-100'
                >
                  <CloseOutlined className='text-xs' />
                </button>
              </div>
            ))}
          </div>
        )}

        <div className='relative flex items-end p-3'>
          <div
            ref={editorRef}
            contentEditable={!disabled}
            className={classNames(
              'min-h-[24px] flex-1 overflow-y-auto whitespace-pre-wrap break-words text-sm outline-none',
              'empty:before:pointer-events-none empty:before:text-gray-400 empty:before:content-[attr(data-placeholder)]',
              disabled && 'cursor-not-allowed opacity-50',
            )}
            style={{ maxHeight }}
            data-placeholder={placeholder || t('input_tips')}
            onInput={handleInput}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            onCompositionStart={() => setIsComposing(true)}
            onCompositionEnd={() => setIsComposing(false)}
            onPaste={handlePaste}
            onDrop={handleDrop}
            onDragOver={e => e.preventDefault()}
          />

          <div className='ml-2 flex items-center gap-2'>
            <label className='cursor-pointer text-gray-400 transition-colors hover:text-gray-600 dark:hover:text-gray-300'>
              <PaperClipOutlined className='text-lg' />
              <input
                type='file'
                accept={ACCEPTED_IMAGE_TYPES.join(',')}
                multiple
                className='hidden'
                onChange={handleFileInputChange}
                disabled={disabled}
              />
            </label>

            <Button
              type='primary'
              size='small'
              icon={loading ? <Spin indicator={<LoadingOutlined />} size='small' /> : <SendOutlined />}
              disabled={disabled || loading || !hasContent}
              onClick={handleSubmit}
              className='flex items-center justify-center'
            />
          </div>
        </div>

        <MentionPopover
          visible={popoverType === 'at'}
          options={mentionFlat}
          activeKey={mentionActive}
          onSelect={handleMentionSelect}
          onClose={() => setPopoverType(null)}
          loading={mentionLoading}
        />

        <CommandPopover
          visible={popoverType === 'slash'}
          commands={commandFlat}
          activeKey={commandActive}
          onSelect={handleCommandSelect}
          onClose={() => setPopoverType(null)}
          loading={commandLoading}
        />
      </div>
    );
  },
);

EnhancedChatInput.displayName = 'EnhancedChatInput';

export default EnhancedChatInput;
