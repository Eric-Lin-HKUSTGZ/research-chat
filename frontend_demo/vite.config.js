import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
// https://vitejs.dev/config/
export default defineConfig({
    // 生产环境使用子路径，开发环境使用根路径
    base: '/digital_twin/research_chat/',
    plugins: [react()],
    server: {
        host: '0.0.0.0',
        port: 5173,
        proxy: {
            // 开发环境代理配置：将 /digital_twin/research_chat/api 代理到后端4200端口
            '/digital_twin/research_chat/api': {
                target: 'http://localhost:4200',
                changeOrigin: true,
                secure: false,
            },
            // WebSocket 代理
            '/digital_twin/research_chat/ws': {
                target: 'ws://localhost:4200',
                changeOrigin: true,
                ws: true,
            }
        }
    },
    build: {
        outDir: 'dist',
        sourcemap: false
    }
});
