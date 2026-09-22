import { FileOutlined, FolderOutlined, UserOutlined } from '@ant-design/icons';
import { Spin } from 'antd';
import classNames from 'classnames';
import React, { useEffect, useRef } from 'react';

export type MentionOption =
  | { type: 'agent'; name: string; display: string; description?: string }
  | { type: 'file'; path: string; display: string; isDirectory?: boolean };

interface MentionPopoverProps {
  visible: boolean;
  options: MentionOption[];
  activeKey: string | null;
  onSelect: (option: MentionOption) => void;
  onClose: () => void;
  position?: { top: number; left: number };
  loading?: boolean;
}

const MentionPopover: React.FC<MentionPopoverProps> = ({
  visible,
  options,
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

  const getKey = (option: MentionOption) => {
    return option.type === 'agent' ? `agent:${option.name}` : `file:${option.path}`;
  };

  const getIcon = (option: MentionOption) => {
    if (option.type === 'agent') {
      return <UserOutlined className='text-blue-500' />;
    }
    return option.isDirectory ? (
      <FolderOutlined className='text-yellow-500' />
    ) : (
      <FileOutlined className='text-gray-500' />
    );
  };

  return (
    <div
      ref={containerRef}
      className='absolute z-50 min-w-[280px] max-w-[400px] max-h-[300px] overflow-y-auto rounded-lg border border-gray-200 bg-white shadow-lg dark:border-gray-700 dark:bg-[#1f2937]'
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
      ) : options.length === 0 ? (
        <div className='px-3 py-2 text-sm text-gray-500 dark:text-gray-400'>No results found</div>
      ) : (
        <div className='py-1'>
          {options.map(option => {
            const key = getKey(option);
            const isActive = key === activeKey;

            return (
              <div
                key={key}
                data-key={key}
                className={classNames(
                  'flex cursor-pointer items-center gap-2 px-3 py-2 text-sm transition-colors',
                  isActive
                    ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
                    : 'text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-800',
                )}
                onClick={() => onSelect(option)}
              >
                {getIcon(option)}
                <span className='flex-1 truncate'>{option.display}</span>
                {option.type === 'agent' && option.description && (
                  <span className='ml-2 truncate text-xs text-gray-400 dark:text-gray-500'>{option.description}</span>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default MentionPopover;
