/**
 * Simple runtime configuration for the RailFair frontend.
 *
 * Set window.__RAILFAIR_API_BASE__ to the origin that serves your backend.
 * 
 * 配置说明：
 * 1. 如果后端部署在 Cloudflare，请将下面的 configuredBase 设置为你的 Cloudflare 后端地址
 *    例如: 'https://your-backend.your-domain.com' 或 'https://your-worker.your-subdomain.workers.dev'
 * 
 * 2. 如果使用 Netlify 代理（推荐），可以留空，然后在 netlify.toml 中配置代理
 * 
 * 3. 本地开发时，可以设置为 'http://localhost:8000'
 */
(function configureRailFair() {
    if (typeof window === 'undefined') {
        return;
    }

    // Cloudflare Workers 后端地址
    // 如果使用 Netlify 代理（推荐），可以留空（使用相对路径）
    // 如果直接调用，设置为: 'https://api.railfair.uk' 或你的 Cloudflare Workers 地址
    // 本地开发时，设置为: 'http://localhost:8000'
    // 生产环境：直接调用后端（绕过 Netlify 代理以避免 Cloudflare 403 错误）
    const configuredBase = 'https://api.railfair.uk';  // 直接调用后端

    if (configuredBase) {
        window.__RAILFAIR_API_BASE__ = configuredBase;
    }
})();

