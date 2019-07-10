// Polyfills.
import 'focus-visible';

// Setup app.
import { createElement, render } from 'preact';

import { Config } from './config';
import BasicLtiLaunchApp from './components/BasicLtiLaunchApp';
import FilePickerApp from './components/FilePickerApp';

const rootEl = document.querySelector('#app');
const config = JSON.parse(document.querySelector('.js-config').textContent);

const mode = config.mode || 'content-item-selection';

render(
  <Config.Provider value={config}>
    {mode === 'basic-lti-launch' && <BasicLtiLaunchApp />}
    {mode === 'content-item-selection' && <FilePickerApp />}
  </Config.Provider>,
  rootEl
);