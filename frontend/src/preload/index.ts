/**
 * Electron Preload Script
 *
 * This script runs in an isolated context and provides a secure bridge
 * between the renderer process and the main process.
 */

import { contextBridge, ipcRenderer } from 'electron';

/**
 * API exposed to the renderer process
 */
const electronAPI = {
  /**
   * Get the application version
   */
  getVersion: (): Promise<string> => {
    return ipcRenderer.invoke('get-app-version');
  },

  /**
   * Get the current platform
   */
  getPlatform: (): Promise<NodeJS.Platform> => {
    return ipcRenderer.invoke('get-platform');
  },

  /**
   * Send a message to the main process
   */
  send: (channel: string, data: unknown): void => {
    const validChannels = ['file-dialog', 'notification'];
    if (validChannels.includes(channel)) {
      ipcRenderer.send(channel, data);
    }
  },

  /**
   * Receive a message from the main process
   */
  on: (channel: string, callback: (...args: unknown[]) => void): void => {
    const validChannels = ['file-selected', 'backend-status'];
    if (validChannels.includes(channel)) {
      ipcRenderer.on(channel, (_event, ...args) => callback(...args));
    }
  },

  /**
   * Remove a listener
   */
  removeListener: (channel: string, callback: (...args: unknown[]) => void): void => {
    ipcRenderer.removeListener(channel, callback);
  },
};

// Expose the API to the renderer
contextBridge.exposeInMainWorld('electronAPI', electronAPI);

// TypeScript declaration for the exposed API
declare global {
  interface Window {
    electronAPI: typeof electronAPI;
  }
}
