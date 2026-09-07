// frontend/src/api/modules/knowledge.ts
import api from '../client'

export interface KGNode {
  id: string
  type: string
  label: string
  props: Record<string, unknown>
  depth?: number
}

export interface KGEdge {
  id: number
  src: string
  dst: string
  type: string
  props: Record<string, unknown>
}

export interface KGStats {
  nodes: number
  edges: number
  node_types: Record<string, number>
  edge_types: Record<string, number>
  case_count?: number
}

export interface GraphResp {
  success: boolean
  seeded: boolean
  nodes: KGNode[]
  edges: KGEdge[]
  stats: KGStats
}

export interface NodeResp {
  success: boolean
  node: KGNode
  neighbors: Record<string, KGNode[]>
}

export interface StatsResp extends KGStats {
  seeded: boolean
}

export const knowledgeService = {
  graph: (nodeTypes?: string[], live = true) =>
    api.get<unknown, GraphResp>('/v1/knowledge/graph', {
      params: {
        ...(nodeTypes?.length ? { node_types: nodeTypes.join(',') } : {}),
        live,
      },
    }),
  node: (id: string) =>
    api.get<unknown, NodeResp>(`/v1/knowledge/node/${encodeURIComponent(id)}`),
  stats: () => api.get<unknown, StatsResp>('/v1/knowledge/stats'),
}
