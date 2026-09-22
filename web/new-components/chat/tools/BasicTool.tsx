import classNames from 'classnames';
import { ReactNode, useEffect, useState } from 'react';
import { IconName, ToolIcon } from '../icons/ToolIcon';
import { Collapsible } from './Collapsible';

export interface TriggerTitle {
  title: string;
  titleClass?: string;
  subtitle?: string;
  subtitleClass?: string;
  args?: string[];
  argsClass?: string;
  action?: ReactNode;
}

const isTriggerTitle = (val: unknown): val is TriggerTitle => {
  return typeof val === 'object' && val !== null && 'title' in val && typeof (val as TriggerTitle).title === 'string';
};

export interface BasicToolProps {
  icon: IconName;
  trigger: TriggerTitle | ReactNode;
  children?: ReactNode;
  hideDetails?: boolean;
  defaultOpen?: boolean;
  forceOpen?: boolean;
  locked?: boolean;
  onSubtitleClick?: () => void;
  className?: string;
}

export function BasicTool({
  icon,
  trigger,
  children,
  hideDetails = false,
  defaultOpen = false,
  forceOpen = false,
  locked = false,
  onSubtitleClick,
  className,
}: BasicToolProps) {
  const [open, setOpen] = useState(defaultOpen);

  useEffect(() => {
    if (forceOpen) setOpen(true);
  }, [forceOpen]);

  const handleOpenChange = (value: boolean) => {
    if (locked && !value) return;
    setOpen(value);
  };

  const hasContent = children && !hideDetails;

  return (
    <Collapsible open={open} onOpenChange={handleOpenChange} className={className}>
      <Collapsible.Trigger>
        <div
          data-component='tool-trigger'
          className={classNames(
            'oc-tool-trigger',
            'flex items-center justify-between w-full',
            'px-3 py-2 rounded-lg',
            'bg-gray-50 dark:bg-gray-800/50',
            'hover:bg-gray-100 dark:hover:bg-gray-700/50',
            'transition-colors duration-150',
            'border border-transparent',
            {
              'border-gray-200 dark:border-gray-700': open,
            },
          )}
        >
          <div data-slot='basic-tool-trigger-content' className='flex items-center gap-2.5 flex-1 min-w-0'>
            <ToolIcon name={icon} size='small' className='text-gray-500 dark:text-gray-400 flex-shrink-0' />
            <div data-slot='basic-tool-info' className='flex-1 min-w-0'>
              {isTriggerTitle(trigger) ? (
                <div data-slot='basic-tool-info-structured' className='flex items-center justify-between gap-2'>
                  <div data-slot='basic-tool-info-main' className='flex items-center gap-2 min-w-0 flex-1'>
                    <span
                      data-slot='basic-tool-title'
                      className={classNames('text-sm font-medium text-gray-700 dark:text-gray-300', trigger.titleClass)}
                    >
                      {trigger.title}
                    </span>
                    {trigger.subtitle && (
                      <span
                        data-slot='basic-tool-subtitle'
                        className={classNames(
                          'text-sm text-gray-500 dark:text-gray-400 truncate',
                          trigger.subtitleClass,
                          {
                            'cursor-pointer hover:text-blue-500 dark:hover:text-blue-400': onSubtitleClick,
                          },
                        )}
                        onClick={e => {
                          if (onSubtitleClick) {
                            e.stopPropagation();
                            onSubtitleClick();
                          }
                        }}
                      >
                        {trigger.subtitle}
                      </span>
                    )}
                    {trigger.args?.map((arg, index) => (
                      <span
                        key={index}
                        data-slot='basic-tool-arg'
                        className={classNames(
                          'text-xs text-gray-400 dark:text-gray-500 px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700',
                          trigger.argsClass,
                        )}
                      >
                        {arg}
                      </span>
                    ))}
                  </div>
                  {trigger.action && (
                    <div data-slot='basic-tool-action' className='flex-shrink-0'>
                      {trigger.action}
                    </div>
                  )}
                </div>
              ) : (
                trigger
              )}
            </div>
          </div>
          {hasContent && !locked && <Collapsible.Arrow />}
        </div>
      </Collapsible.Trigger>
      {hasContent && (
        <Collapsible.Content>
          <div
            data-slot='basic-tool-content'
            className='mt-1 ml-6 pl-3 border-l-2 border-gray-200 dark:border-gray-700'
          >
            {children}
          </div>
        </Collapsible.Content>
      )}
    </Collapsible>
  );
}

export interface GenericToolProps {
  tool: string;
  hideDetails?: boolean;
  className?: string;
}

export function GenericTool({ tool, hideDetails, className }: GenericToolProps) {
  return <BasicTool icon='mcp' trigger={{ title: tool }} hideDetails={hideDetails} className={className} />;
}

export default BasicTool;
