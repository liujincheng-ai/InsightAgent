import { Spin } from 'antd';
import classNames from 'classnames';
import React, { useEffect, useRef } from 'react';

export interface SlashCommand {
  id: string;
  trigger: string;
  title: string;
  description?: string;
  keybind?: string;
  type: 'builtin' | 'custom';
}

interface CommandPopoverProps {
  visible: boolean;
  commands: SlashCommand[];
  activeKey: string | null;
  onSelect: (command: SlashCommand) => void;
  onClose: () => void;
  position?: { top: number; left: number };
  loading?: boolean;
}

const CommandPopover: React.FC<CommandPopoverProps> = ({
  visible,
  commands,
  activeKey,
  onSelect,
  onClose,
  position,
  loading = false,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!visible) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        onClose();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [visible, onClose]);

  useEffect(() => {
    if (!visible || !activeKey || !containerRef.current) return;

    const activeElement = containerRef.current.querySelector(`[data-key="${activeKey}"]`);
    activeElement?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }, [visible, activeKey]);

  if (!visible) return null;

  return (
    <div
      ref={containerRef}
      className='absolute z-50 min-w-[320px] max-w-[450px] max-h-[350px] overflow-y-auto rounded-lg border border-gray-200 bg-white shadow-lg dark:border-gray-700 dark:bg-[#1f2937]'
      style={{
        bottom: position?.top ?? '100%',
        left: position?.left ?? 0,
        marginBottom: 8,
      }}
    >
      {loading ? (
        <div className='flex items-center justify-center py-4'>
          <Spin size='small' />
        </div>
      ) : commands.length === 0 ? (
        <div className='px-3 py-2 text-sm text-gray-500 dark:text-gray-400'>No commands found</div>
      ) : (
        <div className='py-1'>
          {commands.map(command => {
            const isActive = command.id === activeKey;

            return (
              <div
                key={command.id}
                data-key={command.id}
                className={classNames(
                  'flex cursor-pointer items-center justify-between px-3 py-2 text-sm transition-colors',
                  isActive
                    ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
                    : 'text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-800',
                )}
                onClick={() => onSelect(command)}
              >
                <div className='flex flex-col gap-0.5 flex-1 min-w-0'>
                  <div className='flex items-center gap-2'>
                    <span className='font-mono text-blue-600 dark:text-blue-400'>/{command.trigger}</span>
                    <span className='truncate text-gray-600 dark:text-gray-400'>{command.title}</span>
                    {command.type === 'custom' && (
                      <span className='rounded bg-purple-100 px-1.5 py-0.5 text-xs text-purple-600 dark:bg-purple-900/30 dark:text-purple-400'>
                        custom
                      </span>
                    )}
                  </div>
                  {command.description && (
                    <span className='truncate text-xs text-gray-400 dark:text-gray-500'>{command.description}</span>
                  )}
                </div>
                {command.keybind && (
                  <kbd className='ml-2 rounded border border-gray-200 bg-gray-50 px-1.5 py-0.5 text-xs text-gray-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-400'>
                    {command.keybind}
                  </kbd>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default CommandPopover;
