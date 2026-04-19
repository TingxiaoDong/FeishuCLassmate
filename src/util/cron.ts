/**
 * Thin cron wrapper on top of node-cron that supports abort via AbortSignal
 * (matches the OpenClaw service lifecycle signature).
 */

import cron, { type ScheduledTask } from 'node-cron';

export interface CronHandle {
  stop: () => void;
}

export function scheduleCron(
  expression: string,
  handler: () => void | Promise<void>,
  signal?: AbortSignal,
): CronHandle {
  if (!cron.validate(expression)) {
    throw new Error(`invalid cron expression: ${expression}`);
  }

  const task: ScheduledTask = cron.schedule(expression, async () => {
    try {
      await handler();
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error('[feishu-classmate/cron] handler threw:', err);
    }
  });

  const stop = () => task.stop();
  if (signal) {
    if (signal.aborted) {
      stop();
    } else {
      signal.addEventListener('abort', stop, { once: true });
    }
  }

  return { stop };
}
