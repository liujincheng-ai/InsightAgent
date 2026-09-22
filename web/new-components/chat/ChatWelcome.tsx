import { DatabaseOutlined, FileTextOutlined, RobotOutlined, ThunderboltOutlined } from '@ant-design/icons';
import classNames from 'classnames';
import Image from 'next/image';
import React, { memo } from 'react';
import { useTranslation } from 'react-i18next';

interface SuggestionItem {
  icon: React.ReactNode;
  title: string;
  description: string;
  prompt: string;
  onClick?: () => void;
}

interface ChatWelcomeProps {
  userName?: string;
  suggestions?: SuggestionItem[];
  onSuggestionClick?: (suggestion: SuggestionItem) => void;
  className?: string;
  children?: React.ReactNode;
}

const defaultSuggestions: SuggestionItem[] = [
  {
    icon: <DatabaseOutlined className='text-blue-500' />,
    title: '主演示：销售下滑诊断',
    description: '联合数据库、领域 Tool 与企业制度生成经营分析报告',
    prompt:
      '分析 2026 年第二季度华东区域刹车系统配件销售下滑的主要因素，并结合经销商管理制度提出改进建议，生成带图表和引用依据的经营分析报告。',
  },
  {
    icon: <FileTextOutlined className='text-green-500' />,
    title: '制度依据',
    description: '检索经销商考核与重点客户预警条款',
    prompt: '经销商连续两个月销售下降时，企业制度要求采取哪些措施？请引用具体制度和章节。',
  },
  {
    icon: <ThunderboltOutlined className='text-amber-500' />,
    title: '客户流失预警',
    description: '识别停止采购或大幅下滑的核心客户',
    prompt: '分析 2026Q2 华东区域刹车系统的客户流失风险，列出下降贡献最大的 A 级客户并说明口径。',
  },
  {
    icon: <RobotOutlined className='text-purple-500' />,
    title: '经销商健康度',
    description: '按销售、活跃度、折扣和毛利识别优先干预对象',
    prompt: '评估 2026Q2 华东区域经销商健康度，列出高风险对象、扣分项和业务边界。',
  },
];

const ChatWelcome: React.FC<ChatWelcomeProps> = ({
  userName,
  suggestions = defaultSuggestions,
  onSuggestionClick,
  className,
  children,
}) => {
  const { t } = useTranslation();

  const getGreeting = (): string => {
    const hour = new Date().getHours();
    if (hour < 12) return String(t('good_morning', 'Good morning'));
    if (hour < 18) return String(t('good_afternoon', 'Good afternoon'));
    return String(t('good_evening', 'Good evening'));
  };

  return (
    <div
      className={classNames(
        'flex flex-col items-center justify-center min-h-[60vh] px-4 py-12',
        'oc-animate-fade-in',
        className,
      )}
    >
      <div className='flex flex-col items-center max-w-2xl w-full'>
        <div className='flex items-center justify-center w-20 h-20 mb-6 rounded-2xl bg-gradient-to-br from-blue-500 to-blue-600 shadow-lg'>
          <Image
            src='/pictures/logo.png'
            alt='InsightAgent'
            width={48}
            height={48}
            className='object-contain'
            onError={e => {
              const target = e.target as HTMLImageElement;
              target.style.display = 'none';
            }}
          />
        </div>

        <h1 className='text-2xl sm:text-3xl font-semibold text-[var(--oc-text-strong)] mb-2 text-center'>
          InsightAgent
        </h1>

        <p className='text-base text-[var(--oc-text-weak)] mb-8 text-center max-w-md'>
          企业经营数据与知识协同分析智能体
          <span className='block mt-1 text-sm'>汽车配件销售经营分析场景</span>
          {userName && (
            <span className='block mt-1 text-xs'>
              {getGreeting()}，{userName}
            </span>
          )}
        </p>

        {children}

        <div className='grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-xl'>
          {suggestions.map((suggestion, index) => (
            <button
              key={index}
              type='button'
              className={classNames(
                'flex items-start gap-3 p-4 rounded-xl text-left',
                'bg-[var(--oc-surface-raised)] border border-[var(--oc-border-weak)]',
                'hover:border-[var(--oc-border-base)] hover:shadow-md',
                'transition-all duration-200',
                'group',
              )}
              onClick={() => {
                suggestion.onClick?.();
                onSuggestionClick?.(suggestion);
              }}
            >
              <div
                className={classNames(
                  'flex items-center justify-center w-10 h-10 rounded-lg flex-shrink-0',
                  'bg-[var(--oc-surface-base)] group-hover:bg-[var(--oc-surface-hover)]',
                  'transition-colors',
                )}
              >
                {suggestion.icon}
              </div>
              <div className='flex flex-col min-w-0'>
                <span className='text-sm font-medium text-[var(--oc-text-strong)] truncate'>{suggestion.title}</span>
                <span className='text-xs text-[var(--oc-text-weak)] line-clamp-2'>{suggestion.description}</span>
              </div>
            </button>
          ))}
        </div>

        <div className='mt-8 flex items-center gap-2 text-xs text-[var(--oc-text-weaker)]'>
          <span className='font-medium text-[var(--oc-text-weak)]'>InsightAgent</span>
          <span>Evidence-first analytics</span>
        </div>

        <p className='mt-6 text-xs text-[var(--oc-text-weaker)]'>Structured data · domain tools · cited knowledge</p>
      </div>
    </div>
  );
};

export default memo(ChatWelcome);
