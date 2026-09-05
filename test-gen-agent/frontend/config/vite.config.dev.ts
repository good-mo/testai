import { resolveAllowedHosts } from './utils';
import baseConfig from './vite.config.base';
import dotenv from 'dotenv';
import { existsSync, readFileSync } from 'node:fs';
import { mergeConfig } from 'vite';
import eslint from 'vite-plugin-eslint';

// 注入本地/开发配置环境变量(先导入的配置优先级高)
dotenv.config({ path: ['.env.development.local', '.env.development'] });

// 判断是否在容器内运行：容器内必须监听 0.0.0.0，否则宿主机/外部无法访问（如 docker-compose 端口映射）
function isRunningInContainer(): boolean {
  if (process.env.IN_DOCKER === 'true') {
    return true;
  }
  try {
    if (existsSync('/.dockerenv')) {
      return true;
    }
    const cgroup = readFileSync('/proc/1/cgroup', 'utf-8');
    return /docker|kubepods|containerd|crio|\/cnb-/.test(cgroup);
  } catch {
    return false;
  }
}

// 监听地址优先级：VITE_DEV_HOST 显式指定 > 容器内 0.0.0.0 > 本地 localhost
// 需要局域网/公网（cnb.run）访问时可设 VITE_DEV_HOST=0.0.0.0
const devHost = process.env.VITE_DEV_HOST || (isRunningInContainer() ? '0.0.0.0' : 'localhost');

// 允许通过 VITE_DEV_PORT 覆盖端口（默认 5173，与 docker-compose / dev 脚本保持一致）
const devPort = Number.parseInt(process.env.VITE_DEV_PORT ?? '5173', 10);

export default mergeConfig(
  {
    mode: 'development',
    server: {
      // 容器内无法自动打开浏览器，仅本地开发时自动打开
      open: devHost === 'localhost',
      host: devHost,
      port: devPort,
      strictPort: false,
      // Vite 5.4.x 起默认只放行 localhost，这里补充 CNB 开发云 / 内网穿透域名白名单
      // 详见 config/utils/index.ts 的 resolveAllowedHosts()
      allowedHosts: resolveAllowedHosts(),
      fs: {
        strict: true,
      },
      proxy: {
        '/ws': {
          target: process.env.VITE_DEV_DOMAIN,
          changeOrigin: true,
          rewrite: (path: string) => path.replace(/^\/front\/ws/, ''),
          ws: true,
        },
        '/front': {
          target: process.env.VITE_DEV_DOMAIN,
          changeOrigin: true,
          rewrite: (path: string) => path.replace(/^\/front/, ''),
        },
        '/file': {
          target: process.env.VITE_DEV_DOMAIN,
          changeOrigin: true,
          rewrite: (path: string) => path.replace(/^\/front\/file/, ''),
        },
        '/attachment': {
          target: process.env.VITE_DEV_DOMAIN,
          changeOrigin: true,
          rewrite: (path: string) => path.replace(/^\/front\/attachment/, ''),
        },
        '/bug/attachment': {
          target: process.env.VITE_DEV_DOMAIN,
          changeOrigin: true,
          rewrite: (path: string) => path.replace(/^\/front\/bug\/attachment/, ''),
        },
        '/test-plan/report': {
          target: process.env.VITE_DEV_DOMAIN,
          changeOrigin: true,
          rewrite: (path: string) => path.replace(/^\/front\/test-plan\/report/, ''),
        },
        '/organization': {
          target: process.env.VITE_DEV_DOMAIN,
          changeOrigin: true,
          rewrite: (path: string) => path.replace(/^\/front\/organization/, ''),
        },
        '/project': {
          target: process.env.VITE_DEV_DOMAIN,
          changeOrigin: true,
          rewrite: (path: string) => path.replace(/^\/front\/project/, ''),
        },
        '/plugin/image': {
          target: process.env.VITE_DEV_DOMAIN,
          changeOrigin: true,
          rewrite: (path: string) => path.replace(/^\/front\/plugin\/image/, ''),
        },
        '/base-display': {
          target: process.env.VITE_DEV_DOMAIN,
          changeOrigin: true,
          rewrite: (path: string) => path.replace(/^\/front\/base-display/, ''),
        },
      },
    },
    plugins: [
      eslint({
        cache: false,
        include: ['src/**/*.ts', 'src/**/*.tsx', 'src/**/*.vue'],
        exclude: ['node_modules'],
      }),
    ],
  },
  baseConfig
);
