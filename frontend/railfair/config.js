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

    // ⚠️ 重要：请将下面的地址替换为你的 Cloudflare 后端地址
    // 例如: 'https://railfair-api.your-domain.com' 或 'https://railfair-backend.workers.dev'
    const configuredBase = '';

    if (configuredBase) {
        window.__RAILFAIR_API_BASE__ = configuredBase;
    }
})();

