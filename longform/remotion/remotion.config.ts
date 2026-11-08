import {Config} from '@remotion/cli/config';
import fs from 'fs';
// the sandbox's preinstalled headless shell; its versioned path changes between images, so take the first that exists
const candidates = [
  process.env.REMOTION_BROWSER || '',
  '/opt/pw-browsers/chromium_headless_shell',
  '/opt/pw-browsers/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell',
  '/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell',
].filter((p) => p && fs.existsSync(p));
if (candidates.length) Config.setBrowserExecutable(candidates[0]);
Config.setChromiumOpenGlRenderer('swangle');
