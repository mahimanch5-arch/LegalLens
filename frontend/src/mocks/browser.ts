import { setupWorker } from 'msw/browser';
import { authHandlers } from './handlers/auth';
import { conversationHandlers } from './handlers/conversations';
import { documentHandlers } from './handlers/documents';

export const handlers = [...authHandlers, ...conversationHandlers, ...documentHandlers];

export const worker = setupWorker(...handlers);
