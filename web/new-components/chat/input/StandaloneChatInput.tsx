import { StopOutlined } from '@ant-design/icons';
import { Button } from 'antd';
import classNames from 'classnames';
import React, { forwardRef, memo, useImperativeHandle, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { SlashCommand } from './CommandPopover';
import EnhancedChatInput, { ContentPart, EnhancedChatInputRef } from './EnhancedChatInput';

export interface StandaloneChatInputRef {
  focus: () => void;
  clear: () => void;
  getValue: () => string;
  setValue: (value: string) => void;
}

interface StandaloneChatInputProps {
  onSubmit: (text: string, parts: ContentPart[]) => void;
  onStop?: () => void;
  disabled?: boolean;
  loading?: boolean;
  placeholder?: string;
  agents?: Array<{ name: string; description?: string }>;
  commands?: SlashCommand[];
  onFileSearch?: (query: string) => Promise<string[]>;
  onCommandSelect?: (command: SlashCommand) => void;
  children?: React.ReactNode;
  className?: string;
}

const defaultCommands: SlashCommand[] = [
  {
    id: 'clear',
    trigger: 'clear',
    title: 'Clear chat',
    description: 'Clear the conversation history',
    type: 'builtin',
  },
  { id: 'help', trigger: 'help', title: 'Help', description: 'Show available commands', type: 'builtin' },
];

const StandaloneChatInput = forwardRef<StandaloneChatInputRef, StandaloneChatInputProps>(
  (
    {
      onSubmit,
      onStop,
      disabled = false,
      loading = false,
      placeholder,
      agents = [],
      commands = defaultCommands,
      onFileSearch,
      onCommandSelect,
      children,
      className,
    },
    ref,
  ) => {
    const { t } = useTranslation();
    const enhancedInputRef = useRef<EnhancedChatInputRef>(null);

    useImperativeHandle(ref, () => ({
      focus: () => enhancedInputRef.current?.focus(),
      clear: () => enhancedInputRef.current?.clear(),
      getValue: () => enhancedInputRef.current?.getValue() || '',
      setValue: (value: string) => enhancedInputRef.current?.setValue(value),
    }));

    const handleSubmit = (text: string, parts: ContentPart[]) => {
      if (!text.trim() && parts.filter(p => p.type === 'image').length === 0) return;
      onSubmit(text, parts);
      enhancedInputRef.current?.clear();
    };

    return (
      <div
        className={classNames(
          'flex flex-col w-full max-w-3xl mx-auto px-4 py-4',
          'bg-[var(--oc-background-base)]',
          className,
        )}
      >
        {children && <div className='mb-3'>{children}</div>}

        <div
          className={classNames(
            'flex flex-col rounded-xl',
            'bg-[var(--oc-surface-raised)] border border-[var(--oc-border-weak)]',
            'shadow-sm hover:shadow-md transition-shadow',
            'focus-within:border-[var(--oc-border-focus)] focus-within:shadow-md',
          )}
        >
          <EnhancedChatInput
            ref={enhancedInputRef}
            onSubmit={handleSubmit}
            disabled={disabled || loading}
            loading={loading}
            placeholder={placeholder || t('input_tips')}
            agents={agents}
            commands={commands}
            onFileSearch={onFileSearch}
            onCommandSelect={onCommandSelect}
            className='border-0 bg-transparent shadow-none'
            maxHeight={180}
          />
        </div>

        {loading && onStop && (
          <div className='flex justify-center mt-3'>
            <Button
              type='default'
              size='small'
              icon={<StopOutlined />}
              onClick={onStop}
              className={classNames(
                'flex items-center gap-1.5',
                'bg-[var(--oc-surface-raised)] border-[var(--oc-border-base)]',
                'text-[var(--oc-text-base)] hover:text-[var(--oc-error-text)]',
                'hover:border-[var(--oc-error-base)]',
              )}
            >
              {t('stop_generating', 'Stop generating')}
            </Button>
          </div>
        )}

        <div className='flex items-center justify-center mt-2 text-xs text-[var(--oc-text-weaker)]'>
          <span>
            Press{' '}
            <kbd className='px-1.5 py-0.5 mx-0.5 rounded bg-[var(--oc-surface-base)] border border-[var(--oc-border-weak)] font-mono text-[10px]'>
              Enter
            </kbd>{' '}
            to send,{' '}
            <kbd className='px-1.5 py-0.5 mx-0.5 rounded bg-[var(--oc-surface-base)] border border-[var(--oc-border-weak)] font-mono text-[10px]'>
              Shift+Enter
            </kbd>{' '}
            for new line
          </span>
        </div>
      </div>
    );
  },
);

StandaloneChatInput.displayName = 'StandaloneChatInput';

export default memo(StandaloneChatInput);
