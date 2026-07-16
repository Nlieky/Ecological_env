# 废水监测系统前端

## 技术栈
- Vue 3.5 (Composition API)
- TypeScript
- Vite 6
- Pinia 3 (状态管理)
- Element Plus 2 (UI组件库)
- Axios 1 (HTTP客户端)
- ECharts 5 (数据可视化)

## 架构
```
Views (页面层)
  ↓
Stores (状态管理层) - Pinia
  ↓
Composables (业务逻辑复用层)
  ↓
API Services (API层)
  ↓
HTTP Client (axios)
  ↓
Backend FastAPI
```

## 目录结构
src/
├── api/              # API层
│   ├── client.ts     # 统一HTTP客户端
│   ├── services/     # API服务
│   └── types/        # API类型定义
├── composables/      # 业务逻辑复用
├── stores/           # Pinia状态管理
├── types/            # 业务类型定义
├── components/       # Vue组件
├── views/            # 页面组件
└── router/           # 路由配置

## 开发
```bash
npm install
npm run dev
npm run type-check
npm run build
```

## API集成
- queryService - 查询接口
- realtimeService - 实时数据接口
- eventsService - 事件管理接口
- logsService - 日志查询接口

## 状态管理
- useChatStore - 聊天状态
- useRealtimeStore - 实时数据状态
- useEventsStore - 事件状态

## 业务逻辑复用
- useQueryAgent - 查询智能体逻辑
- useRealtimePolling - 实时数据轮询
- useEvidenceChain - 证据链展示
