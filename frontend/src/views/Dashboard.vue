<template>
  <section class="page">
    <header class="page-head">
      <div>
        <h2>运营概览</h2>
        <p class="page-desc">汇总各业务模块的关键指标，先看总量再看异常。</p>
      </div>
    </header>
    <div class="stat-row">
      <article v-for="card in cards" :key="card.label" class="stat-card">
        <span class="stat-label">{{ card.label }}</span>
        <strong class="stat-value">{{ card.value }}</strong>
      </article>
    </div>

    <section class="todo-panel" data-testid="complaint-todo-panel">
      <div class="todo-head">
        <div>
          <h3>公众诉求待办清单</h3>
          <p class="page-desc">汇总待受理、办理中和已回复诉求；待办 {{ complaintTodos.length }} 条，与公众诉求待办列表一致。</p>
        </div>
        <RouterLink class="btn" to="/complaint">进入诉求列表</RouterLink>
      </div>
      <table class="data-table" data-testid="complaint-todo-table">
        <thead>
          <tr>
            <th>诉求编号</th>
            <th>诉求来源</th>
            <th>诉求内容</th>
            <th>办理期限</th>
            <th>状态</th>
            <th>异常原因</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in complaintTodos" :key="String(row.id)" :class="{ 'abnormal-row': Boolean(row.abnormal) }">
            <td>{{ row['诉求编号'] || '—' }}</td>
            <td :class="{ 'missing-value': !row['诉求来源'] }">{{ row['诉求来源'] || '来源缺失' }}</td>
            <td>{{ row['诉求内容'] || '—' }}</td>
            <td>{{ row['办理期限'] || '—' }}</td>
            <td>{{ row.status }}</td>
            <td>
              <span v-if="reasons(row).length" class="abnormal-reason">{{ reasons(row).join('；') }}</span>
              <span v-else>—</span>
            </td>
          </tr>
          <tr v-if="!complaintTodos.length">
            <td colspan="6" class="empty-state">当前待办范围内没有待受理、办理中或已回复的公众诉求。</td>
          </tr>
        </tbody>
      </table>
    </section>

    <table class="data-table overview-table">
      <thead>
        <tr><th>业务模块</th><th>今日新增</th><th>待处理</th><th>异常量</th></tr>
      </thead>
      <tbody>
        <tr v-for="row in moduleRows" :key="row.name">
          <td>{{ row.name }}</td>
          <td>{{ row.created }}</td>
          <td>{{ row.pending }}</td>
          <td>{{ row.abnormal }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { fetchJson, request } from '@/api/client'

type Overview = {
  cards: { label: string; value: number }[]
  modules: { name: string; created: number; pending: number; abnormal: number }[]
}
type ComplaintRow = Record<string, string | number | boolean | string[] | null>
type ComplaintPage = { items?: ComplaintRow[]; total?: number }

const fallbackModules: Overview['modules'] = [
  { name: '管段档案', created: 0, pending: 0, abnormal: 0 },
  { name: '检查井', created: 0, pending: 0, abnormal: 0 },
  { name: '阀门井室', created: 0, pending: 0, abnormal: 0 },
  { name: '泵站设施', created: 0, pending: 0, abnormal: 0 },
  { name: '巡查任务', created: 0, pending: 0, abnormal: 0 },
  { name: '缺陷登记', created: 0, pending: 0, abnormal: 0 },
  { name: '内窥检测', created: 0, pending: 0, abnormal: 0 },
  { name: '修复施工', created: 0, pending: 0, abnormal: 0 },
  { name: '压力监测', created: 0, pending: 0, abnormal: 0 },
  { name: '流量监测', created: 0, pending: 0, abnormal: 0 },
  { name: '泄漏排查', created: 0, pending: 0, abnormal: 0 },
  { name: '清淤疏浚', created: 0, pending: 0, abnormal: 0 },
  { name: '养护材料', created: 0, pending: 0, abnormal: 0 },
  { name: '养护机械', created: 0, pending: 0, abnormal: 0 },
  { name: '占道许可', created: 0, pending: 0, abnormal: 0 },
  { name: '公众诉求', created: 0, pending: 0, abnormal: 0 },
  { name: '养护资金', created: 0, pending: 0, abnormal: 0 },
  { name: '管网档案', created: 0, pending: 0, abnormal: 0 },
]

const cards = ref<Overview['cards']>([])
const moduleRows = ref<Overview['modules']>(fallbackModules)
const complaintTodos = ref<ComplaintRow[]>([])

function reasons(row: ComplaintRow): string[] {
  const value = row.abnormal_reasons
  return Array.isArray(value) ? value.map(String) : []
}

onMounted(async () => {
  try {
    const payload = await fetchJson<Overview>('/api/overview')
    cards.value = payload.cards
    moduleRows.value = payload.modules
  } catch {
    cards.value = [
      { label: '业务模块', value: fallbackModules.length },
      { label: '今日新增', value: 0 },
      { label: '待处理', value: 0 },
    ]
  }

  try {
    const response = await request('/api/complaint?scope=todo&size=200')
    if (!response.ok) throw new Error('诉求待办读取失败')
    const payload = await response.json() as ComplaintPage
    complaintTodos.value = payload.items ?? []
  } catch {
    complaintTodos.value = []
  }
})
</script>
