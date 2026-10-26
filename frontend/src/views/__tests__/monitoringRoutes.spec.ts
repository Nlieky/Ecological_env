import { afterEach, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import appRouter from '@/router'

vi.mock('vue-router', async importOriginal => {
  const actual = await importOriginal<typeof import('vue-router')>()
  return { ...actual, createWebHistory: actual.createMemoryHistory }
})
afterEach(() => vi.unstubAllGlobals())

it('preserves a decoded factory identifier when following an old single-plant link', async () => {
  // Exercise the production route records while avoiding unrelated lazy views.
  const lightweight = (record: any): any => ({ ...record,
    ...(record.component ? { component: { render: () => null } } : {}),
    ...(record.children ? { children: record.children.map(lightweight) } : {}),
  })
  const router = createRouter({ history: createMemoryHistory(), routes: appRouter.options.routes.map(lightweight) })
  const plant = '厂 A/一期?#'
  await router.push(`/plants/${encodeURIComponent(plant)}`)
  expect(router.currentRoute.value.path).toBe('/dashboard')
  expect(router.currentRoute.value.query.plant).toBe(plant)
})
