/**
 * 图片占位符处理工具
 *
 * 提供两个函数：
 * - vueHandleImageError(target): 接收 img 元素或事件对象，自动判断
 * - handleImageError(element):  仅接收元素，用于详情页内联 onerror
 */
(function () {
  "use strict";

  // SVG 占位符（Data URI，无外部依赖）
  var PLACEHOLDER_SVG =
    "data:image/svg+xml;utf8," +
    encodeURIComponent(
      '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="260" viewBox="0 0 400 260">' +
        '<rect width="400" height="260" fill="#e8eef8"/>' +
        '<g fill="none" stroke="#9aa7c2" stroke-width="2">' +
        '<rect x="160" y="80" width="80" height="60" rx="4"/>' +
        '<circle cx="180" cy="100" r="8"/>' +
        '<path d="M160 140 L200 110 L240 140"/>' +
        "</g>" +
        '<text x="200" y="180" font-family="system-ui, -apple-system, sans-serif" font-size="14" fill="#73819b" text-anchor="middle">图片加载失败</text>' +
        "</svg>"
    );

  /**
   * 兼容事件对象与元素：返回 img 元素
   */
  function toElement(target) {
    if (!target) return null;
    if (target.tagName && target.tagName.toUpperCase() === "IMG") return target;
    if (target.target) return target.target; // Event
    if (target.srcElement) return target.srcElement; // IE
    return null;
  }

  /**
   * Vue 模板中使用：@error="handleImageError"
   * 此函数会被传入事件对象
   */
  function vueHandleImageError(target) {
    var img = toElement(target);
    if (!img) return;
    img.onerror = null; // 防止无限循环
    if (img.src !== PLACEHOLDER_SVG) {
      img.src = PLACEHOLDER_SVG;
    }
  }

  /**
   * 详情页内联 onerror 使用：onerror="window.handleImageError(this)"
   */
  function handleImageError(element) {
    var img = toElement(element);
    if (!img) return;
    img.onerror = null;
    if (img.src !== PLACEHOLDER_SVG) {
      img.src = PLACEHOLDER_SVG;
    }
  }

  window.vueHandleImageError = vueHandleImageError;
  window.handleImageError = handleImageError;
})();
