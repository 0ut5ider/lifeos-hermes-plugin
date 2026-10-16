// ABOUTME: Measures candidate setup geometry, labels, focus, and text contrast in Hermes.
// ABOUTME: Returns safe presentation metadata without input values or memory content.
(() => {
  const root = document.querySelector('.lifeos-setup');
  if (!root) throw new Error('The candidate setup root is missing');
  const visible = element => element.getBoundingClientRect().height > 0;
  const context = document.createElement('canvas').getContext('2d');
  function rgba(color) {
    context.clearRect(0, 0, 1, 1);
    context.fillStyle = color;
    context.fillRect(0, 0, 1, 1);
    return [...context.getImageData(0, 0, 1, 1).data].map(value => value / 255);
  }
  function blend(top, bottom) {
    const alpha = top[3] + bottom[3] * (1 - top[3]);
    return [...top.slice(0, 3).map((value, index) =>
      (value * top[3] + bottom[index] * bottom[3] * (1 - top[3])) / (alpha || 1)), alpha];
  }
  function background(element) {
    if (!element) return [1, 1, 1, 1];
    const color = rgba(getComputedStyle(element).backgroundColor);
    return color[3] >= .999 ? color : blend(color, background(element.parentElement));
  }
  function luminance(color) {
    return color.slice(0, 3).map(value => value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4)
      .reduce((sum, value, index) => sum + value * [.2126, .7152, .0722][index], 0);
  }
  const text = [...root.querySelectorAll('p,label,h1,h2,h3,h4,button,summary,a')]
    .filter(element => visible(element) && !element.disabled)
    .map(element => {
      const back = background(element);
      const front = blend(rgba(getComputedStyle(element).color), back);
      const values = [luminance(front), luminance(back)].sort((a, b) => a - b);
      return {tag: element.tagName, id: element.id, ratio: Number(((values[1] + .05) / (values[0] + .05)).toFixed(2))};
    });
  const buttons = [...root.querySelectorAll('button')].filter(visible);
  const controls = [...root.querySelectorAll('input,select,textarea')];
  return {
    width: innerWidth,
    overflow: document.documentElement.scrollWidth > innerWidth,
    visibleButtons: buttons.length,
    smallButtons: buttons.filter(button => button.getBoundingClientRect().height < 42).length,
    unstyledButtons: buttons.filter(button => parseFloat(getComputedStyle(button).paddingTop) === 0 ||
      parseFloat(getComputedStyle(button).borderTopWidth) === 0).length,
    unlabeledControls: controls.filter(control => !control.labels?.length &&
      !control.getAttribute('aria-label') && !control.getAttribute('aria-labelledby')).map(control => control.id),
    textContrast: {minimum: Math.min(...text.map(item => item.ratio)), measured: text.length,
      below45: text.filter(item => item.ratio < 4.5)},
    nonGetRequests: (window.__lifeosPreviewCalls ?? []).filter(call => call.method !== 'GET'),
    focus: {visible: document.activeElement.matches(':focus-visible'), outline: getComputedStyle(document.activeElement).outline},
  };
})()
