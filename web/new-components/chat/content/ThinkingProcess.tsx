import classNames from 'classnames';
import React, { useEffect, useState } from 'react';

export interface ThinkingProcessProps {
  content: string;
  enableAnimation?: boolean;
  animationSpeed?: number;
  className?: string;
}

const ThinkingProcess: React.FC<ThinkingProcessProps> = ({
  content,
  enableAnimation = true,
  animationSpeed = 30,
  className,
}) => {
  const [displayedText, setDisplayedText] = useState('');
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    if (!enableAnimation) {
      setDisplayedText(content);
      setIsComplete(true);
      return;
    }

    setDisplayedText('');
    setIsComplete(false);

    let index = 0;
    const timer = setInterval(() => {
      if (index < content.length) {
        const chunkSize = Math.min(3, content.length - index);
        setDisplayedText(prev => prev + content.slice(index, index + chunkSize));
        index += chunkSize;
      } else {
        setIsComplete(true);
        clearInterval(timer);
      }
    }, animationSpeed);

    return () => clearInterval(timer);
  }, [content, enableAnimation, animationSpeed]);

  if (!content) return null;

  return (
    <div
      className={classNames('text-sm text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap', className)}
    >
      {displayedText}
      {!isComplete && <span className='inline-block w-1.5 h-4 ml-1 bg-blue-500 animate-pulse' />}
    </div>
  );
};

export default ThinkingProcess;
