export const VIEWPORTS = Object.freeze({
  compact: { width: 412, height: 915 },
  portrait: { width: 835, height: 1194 },
  landscape: { width: 1195, height: 835 },
  desktop: { width: 1440, height: 900 },
  wide: { width: 2560, height: 1440 },
});

export function viewportUse(alias) {
  return { viewport: VIEWPORTS[alias], hasTouch: ['compact', 'portrait'].includes(alias) };
}
