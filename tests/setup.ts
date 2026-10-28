import '@testing-library/jest-dom/vitest';
import { afterEach, beforeAll } from 'vitest';
import { cleanup } from '@testing-library/react';

// jsdom does not implement canvas, which axe-core needs for one internal step of
// its color-contrast rule (an icon-ligature probe). A minimal measureText stub
// lets that rule evaluate normally; it does not weaken any accessibility check.
beforeAll(() => {
  if (typeof HTMLCanvasElement !== 'undefined') {
    HTMLCanvasElement.prototype.getContext = function getContext() {
      return { measureText: () => ({ width: 0 }) } as unknown as CanvasRenderingContext2D;
    } as unknown as typeof HTMLCanvasElement.prototype.getContext;
  }
});

afterEach(cleanup);
