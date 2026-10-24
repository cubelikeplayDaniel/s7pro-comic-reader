/**
 * 网易有道词典笔 S7 Pro - 漫画阅读器应用入口
 * App ID: 8001888800000001
 * 架构规范: 遵循 Falcon 官方 App/Page 双阶生命周期契约与 $npage 原生返回拦截协议
 */

import RootComponent from './index.js';

class BasePage extends $falcon.Page {
  beforeVueInstantiate(Vue) {
    console.log('[ComicReader] BasePage beforeVueInstantiate');
  }
  onLoad(query) {
    super.onLoad(query);
    console.log('[ComicReader] BasePage onLoad, query:', JSON.stringify(query || {}));
    this.configureNativeWindow();
  }
  onShow() {
    super.onShow();
    console.log('[ComicReader] BasePage onShow');
    this.configureNativeWindow();
  }
  configureNativeWindow() {
    try {
      const npage = this.$npage || (typeof $npage !== 'undefined' ? $npage : null);
      if (npage) {
        if (typeof npage.setSupportTopPanel === 'function') {
          npage.setSupportTopPanel(false);
        }
        if (typeof npage.setDisableLeftSwipeBack === 'function') {
          npage.setDisableLeftSwipeBack(false);
        }
        if (typeof npage.setSupportBack === 'function') {
          npage.setSupportBack(false);
        }
      }
    } catch (e) {}
  }
  onHide() {
    super.onHide();
    console.log('[ComicReader] BasePage onHide');
  }
  onUnload() {
    super.onUnload();
    console.log('[ComicReader] BasePage onUnload');
  }
  onBackPressed() {
    if (this.$root && typeof this.$root.handleMainBack === 'function') {
      this.$root.handleMainBack();
      return true;
    }
    if (typeof this.finish === 'function') {
      this.finish();
    }
    return true;
  }
  backButtonClicked() {
    return this.onBackPressed();
  }
}

class ComicReaderApp extends $falcon.App {
  onLaunch(options) {
    super.onLaunch(options);
    console.log('[ComicReader] App onLaunch, options:', JSON.stringify(options || {}));
    $falcon.useDefaultBasePageClass(BasePage);
  }
  onShow() {
    super.onShow();
    console.log('[ComicReader] App onShow');
  }
  onHide() {
    super.onHide();
    console.log('[ComicReader] App onHide');
  }
  onDestroy() {
    super.onDestroy();
    console.log('[ComicReader] App onDestroy');
  }
}

ComicReaderApp.meta = {
  appName: '漫画阅读器',
  appid: '8001888800000001',
  version: '1.0.2',
  isSingleJsBundle: false
};

ComicReaderApp.__pages = {
  index: RootComponent
};

$falcon.__AppClazz = ComicReaderApp;
$falcon.__loadModuleDefault = async function(pageName) {
  if (ComicReaderApp.__pages && ComicReaderApp.__pages[pageName]) {
    return ComicReaderApp.__pages[pageName];
  }
  const mod = await import('./' + pageName + '.js');
  return mod.default;
};

export default ComicReaderApp;
