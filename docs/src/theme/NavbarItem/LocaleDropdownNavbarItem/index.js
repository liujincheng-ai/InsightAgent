import React, {useState, useRef, useEffect} from 'react';
import clsx from 'clsx';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import {useAlternatePageUtils} from '@docusaurus/theme-common/internal';
import {useCollapsible, Collapsible} from '@docusaurus/theme-common';
import {translate} from '@docusaurus/Translate';
import {useLocation} from '@docusaurus/router';


const localeFlags = {
  en: '🇺🇸',
  'zh-CN': '🇨🇳',
};

function getLocaleLabel(locale, localeConfigs) {
  return localeConfigs[locale]?.label ?? locale;
}

function getLocaleFlag(locale) {
  return localeFlags[locale] ?? '🌐';
}

function renderLocaleNode(locale, localeConfigs) {
  return (
    <>
      <span className="navbar-language-flag" aria-hidden="true">
        {getLocaleFlag(locale)}
      </span>
      <span className="navbar-language-label">{getLocaleLabel(locale, localeConfigs)}</span>
    </>
  );
}

function LocaleDropdownDesktop({currentLocale, localeConfigs, localeItems, className}) {
  const [isOpen, setIsOpen] = useState(false);
  const closeTimerRef = useRef(null);

  function handleMouseEnter() {
    if (closeTimerRef.current) {
      clearTimeout(closeTimerRef.current);
      closeTimerRef.current = null;
    }
    setIsOpen(true);
  }

  function handleMouseLeave() {
    // 短暂延迟关闭，让鼠标有时间移动到下拉菜单上
    closeTimerRef.current = setTimeout(() => {
      setIsOpen(false);
    }, 100);
  }

  useEffect(() => {
    return () => {
      if (closeTimerRef.current) {
        clearTimeout(closeTimerRef.current);
      }
    };
  }, []);

  return (
    <div
      className={clsx(
        'navbar__item',
        'dropdown',
        'dropdown--hoverable',
        {'dropdown--show': isOpen},
        'navbar-language-dropdown',
        className,
      )}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}>
      <a
        href="#"
        aria-haspopup="true"
        aria-expanded={isOpen}
        role="button"
        className="navbar__link"
        onClick={(e) => e.preventDefault()}>
        {renderLocaleNode(currentLocale, localeConfigs)}
      </a>
      <ul className="dropdown__menu">
        {localeItems.map((item, index) => (
          <li key={index}>
            <a
              className={clsx('dropdown__link', item.className)}
              href={item.href}
              target={item.target}
              lang={item.lang}>
              {item.label}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}

function LocaleDropdownMobile({localeItems, className}) {
  const mobileLabel = translate({
    message: 'Languages',
    id: 'theme.navbar.mobileLanguageDropdown.label',
    description: 'The label for the mobile language switcher dropdown',
  });

  const {collapsed, toggleCollapsed} = useCollapsible({initialState: true});

  return (
    <li
      className={clsx('menu__list-item', {
        'menu__list-item--collapsed': collapsed,
      })}>
      <a
        role="button"
        className="menu__link menu__link--sublist menu__link--sublist-caret"
        onClick={(e) => {
          e.preventDefault();
          toggleCollapsed();
        }}
        href="#">
        {mobileLabel}
      </a>
      <Collapsible lazy as="ul" className="menu__list" collapsed={collapsed}>
        {localeItems.map((item, index) => (
          <li key={index} className="menu__list-item">
            <a
              className={clsx('menu__link', item.className)}
              href={item.href}
              target={item.target}
              lang={item.lang}>
              {item.label}
            </a>
          </li>
        ))}
      </Collapsible>
    </li>
  );
}

export default function LocaleDropdownNavbarItem({
  mobile,
  dropdownItemsBefore = [],
  dropdownItemsAfter = [],
  className,
  queryString = '',
  ...props
}) {
  const {
    i18n: {currentLocale, locales, localeConfigs},
  } = useDocusaurusContext();
  const alternatePageUtils = useAlternatePageUtils();
  const {search, hash} = useLocation();

  const localeItems = locales.map((locale) => {
    const href = `${alternatePageUtils.createUrl({
      locale,
      fullyQualified: false,
    })}${search}${hash}${queryString}`;

    return {
      label: renderLocaleNode(locale, localeConfigs),
      lang: localeConfigs[locale]?.htmlLang,
      href,
      target: '_self',
      className:
        locale === currentLocale
          ? mobile
            ? 'menu__link--active'
            : 'dropdown__link--active'
          : '',
    };
  });

  const items = [...dropdownItemsBefore, ...localeItems, ...dropdownItemsAfter];

  if (mobile) {
    return (
      <LocaleDropdownMobile
        localeItems={items}
        className={className}
      />
    );
  }

  return (
    <LocaleDropdownDesktop
      currentLocale={currentLocale}
      localeConfigs={localeConfigs}
      localeItems={items}
      className={className}
    />
  );
}
