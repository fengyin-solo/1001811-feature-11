<template>
  <section class="page" data-module="complaint">
    <header class="page-head">
      <div>
        <h2>公众诉求管理</h2>
        <p class="page-desc">待受理、办理中和已回复的诉求统一进入待办；异常来源与超期记录单独标注，受理草稿中断后可继续。</p>
      </div>
      <div class="page-actions">
        <button class="btn" type="button" @click="exportRows">导出公众诉求清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <div class="scope-tabs" role="tablist" aria-label="诉求清单范围">
      <button
        type="button"
        class="scope-tab"
        :class="{ active: scope === 'todo' }"
        @click="switchScope('todo')"
      >
        待办清单（{{ todoCount }}）
      </button>
      <button
        type="button"
        class="scope-tab"
        :class="{ active: scope === 'all' }"
        @click="switchScope('all')"
      >
        全部诉求（{{ allCount }}）
      </button>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label class="filter-item">
        <span>关键词</span>
        <input v-model="keyword" placeholder="按诉求编号、来源或内容检索" data-testid="complaint-keyword" />
      </label>
      <label class="filter-item">
        <span>诉求状态</span>
        <select v-model="statusFilter" data-testid="complaint-status-filter">
          <option value="">全部状态</option>
          <option v-for="item in statuses" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table" data-testid="complaint-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>异常原因</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="row in rows"
          :key="String(row.id)"
          :class="{ 'abnormal-row': Boolean(row.abnormal) }"
          :data-testid="`complaint-row-${row.id}`"
        >
          <td v-for="column in columns" :key="column">
            <button
              v-if="column === '诉求编号'"
              type="button"
              class="link"
              @click="openDetail(row)"
            >
              {{ displayValue(row, column) }}
            </button>
            <span v-else :class="{ 'missing-value': column === '诉求来源' && !row[column] }">
              {{ displayValue(row, column) }}
            </span>
          </td>
          <td>
            <span v-if="abnormalReasons(row).length" class="abnormal-reason">
              {{ abnormalReasons(row).join('；') }}
            </span>
            <span v-else>—</span>
          </td>
          <td class="row-actions">
            <button
              v-if="row.status === '待受理'"
              class="link"
              type="button"
              data-testid="accept-complaint"
              @click="startAccept(row)"
            >
              {{ hasDraft(row.id) ? '继续受理' : '受理诉求' }}
            </button>
            <button
              v-if="row.status === '办理中'"
              class="link"
              type="button"
              @click="submitAction('提交回复', row)"
            >
              提交回复
            </button>
            <button
              v-if="row.status === '已回复'"
              class="link"
              type="button"
              @click="submitAction('关闭诉求', row)"
            >
              关闭诉求
            </button>
            <button class="link" type="button" @click="openDetail(row)">查看详情</button>
          </td>
        </tr>
        <tr v-if="loading">
          <td :colspan="columns.length + 2" class="empty-state">正在加载公众诉求…</td>
        </tr>
        <tr v-else-if="!rows.length">
          <td :colspan="columns.length + 2" class="empty-state" data-testid="complaint-empty">
            {{ emptyMessage }}
          </td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>当前范围：{{ scopeText }} · 共 {{ total }} 条；待办清单 {{ todoCount }} 条，与诉求待办列表一致</span>
      <span v-if="errorMessage" class="error-text" data-testid="complaint-error">{{ errorMessage }}</span>
    </footer>

    <div v-if="detail" class="modal-mask" @click.self="closeDetail">
      <section class="modal-card" data-testid="complaint-detail">
        <header class="modal-head">
          <div>
            <h3>诉求详情 · {{ detail['诉求编号'] }}</h3>
            <p v-if="detailAbnormalReasons.length" class="abnormal-reason">
              异常：{{ detailAbnormalReasons.join('；') }}
            </p>
          </div>
          <button type="button" class="btn ghost" @click="closeDetail">关闭</button>
        </header>

        <dl class="detail-grid">
          <div v-for="column in columns" :key="column">
            <dt>{{ column }}</dt>
            <dd :class="{ 'missing-value': column === '诉求来源' && !detail[column] }">
              {{ displayValue(detail, column) }}
            </dd>
          </div>
        </dl>

        <form v-if="accepting" class="accept-form" @submit.prevent="submitAccept">
          <label>
            <span>受理人员</span>
            <input
              v-model="acceptForm['受理人员']"
              placeholder="请输入受理人员"
              @input="saveDraft"
            />
          </label>
          <label>
            <span>处理措施 *</span>
            <textarea
              v-model="acceptForm['处理措施']"
              rows="4"
              placeholder="请填写现场核查、派单或协调处理措施"
              data-testid="accept-measure"
              @input="saveDraft"
            ></textarea>
          </label>
          <p class="form-tip">内容会自动保存；提交失败或离开页面后，可从这条诉求继续处理。</p>
          <div class="modal-actions">
            <button class="btn primary" type="submit" :disabled="submitting" data-testid="submit-accept">
              {{ submitting ? '提交中…' : '提交受理' }}
            </button>
            <button class="btn" type="button" @click="cancelAccept">取消</button>
          </div>
        </form>
        <div v-else class="modal-actions">
          <button
            v-if="detail.status === '待受理'"
            class="btn primary"
            type="button"
            data-testid="accept-from-detail"
            @click="startAccept(detail)"
          >
            {{ draftFor(detail.id) ? '继续受理' : '受理诉求' }}
          </button>
          <button
            v-if="detail.status === '办理中'"
            class="btn primary"
            type="button"
            @click="submitAction('提交回复', detail)"
          >
            提交回复
          </button>
          <button
            v-if="detail.status === '已回复'"
            class="btn primary"
            type="button"
            @click="submitAction('关闭诉求', detail)"
          >
            关闭诉求
          </button>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { request } from '@/api/client'

type Row = Record<string, string | number | boolean | string[] | null>
type AcceptForm = {
  '受理人员': string
  '处理措施': string
}

const ENDPOINT = '/api/complaint'
const DRAFT_PREFIX = 'complaint-accept-draft:'
const columns = ['诉求编号', '诉求来源', '诉求内容', '涉及管段', '受理人员', '处理措施', '办理期限', '诉求状态']
const statuses = ['待受理', '办理中', '已回复', '已关闭']

const rows = ref<Row[]>([])
const total = ref(0)
const todoCount = ref(0)
const allCount = ref(0)
const errorMessage = ref('')
const loading = ref(false)
const keyword = ref('')
const statusFilter = ref('')
const scope = ref<'todo' | 'all'>('todo')

const detail = ref<Row | null>(null)
const accepting = ref(false)
const submitting = ref(false)
const acceptForm = ref<AcceptForm>({ '受理人员': '', '处理措施': '' })
let acceptTarget: Row | null = null

const stats = computed(() => [
  { label: '待办诉求', value: todoCount.value },
  { label: '待受理诉求', value: rows.value.filter((row) => row.status === '待受理').length },
  { label: '办理中诉求', value: rows.value.filter((row) => row.status === '办理中').length },
  { label: '已回复诉求', value: rows.value.filter((row) => row.status === '已回复').length },
  { label: '异常诉求', value: rows.value.filter((row) => row.abnormal).length },
])

const scopeText = computed(() => scope.value === 'todo' ? '待办清单：待受理、办理中、已回复' : '全部诉求：含已关闭')
const emptyMessage = computed(() => {
  const filters: string[] = [scopeText.value]
  if (statusFilter.value) filters.push(`状态为「${statusFilter.value}」`)
  if (keyword.value.trim()) filters.push(`关键词包含「${keyword.value.trim()}」`)
  return `当前范围内没有符合条件的新诉求（${filters.join('；')}）。可调整状态、关键词或切换清单范围后再查。`
})
const detailAbnormalReasons = computed(() => (detail.value ? abnormalReasons(detail.value) : []))

function switchScope(nextScope: 'todo' | 'all') {
  scope.value = nextScope
  void reload()
}

function resetFilters() {
  keyword.value = ''
  statusFilter.value = ''
  void reload()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function abnormalReasons(row: Row): string[] {
  const reasons = row.abnormal_reasons
  return Array.isArray(reasons) ? reasons.map(String) : []
}

function displayValue(row: Row, column: string): string {
  if (column === '诉求状态') return String(row.status ?? row['诉求状态'] ?? '—')
  if (column === '诉求来源' && !String(row[column] ?? '').trim()) return '来源缺失'
  const value = row[column]
  return value === null || value === undefined || value === '' ? '—' : String(value)
}

function draftKey(id: unknown): string {
  return `${DRAFT_PREFIX}${String(id)}`
}

function draftFor(id: unknown): AcceptForm | null {
  try {
    const raw = window.localStorage.getItem(draftKey(id))
    return raw ? JSON.parse(raw) as AcceptForm : null
  } catch {
    return null
  }
}

function hasDraft(id: unknown): boolean {
  const draft = draftFor(id)
  return Boolean(draft && (draft['处理措施'] || draft['受理人员']))
}

function saveDraft() {
  if (!acceptTarget) return
  const id = Number(acceptTarget.id)
  if (!id) return
  try {
    window.localStorage.setItem(draftKey(id), JSON.stringify(acceptForm.value))
  } catch {
    // 隐私模式或存储不可用时仍允许本次提交，不阻断受理流程。
  }
}

function clearDraft(id: unknown) {
  try {
    window.localStorage.removeItem(draftKey(id))
  } catch {
    // 草稿清理失败不影响状态已经提交成功的结果。
  }
}

async function openDetail(row: Row) {
  errorMessage.value = ''
  detail.value = row
  accepting.value = false
  try {
    const response = await request(`${ENDPOINT}/${row.id}`)
    const payload = await response.json()
    if (!response.ok) throw new Error(payload.detail || '诉求详情读取失败')
    detail.value = payload as Row
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '诉求详情读取失败'
  }
}

function closeDetail() {
  detail.value = null
  accepting.value = false
  acceptTarget = null
  void reload()
}

async function startAccept(row: Row) {
  errorMessage.value = ''
  detail.value = row
  accepting.value = true
  acceptTarget = row
  await openDetail(row)
  const latest = detail.value ?? row
  if (latest.status !== '待受理') {
    accepting.value = false
    errorMessage.value = '该诉求已受理或已进入后续环节，重复受理不会再次生效'
    return
  }
  accepting.value = true
  acceptTarget = latest
  const draft = draftFor(String(latest.id))
  acceptForm.value = {
    '受理人员': draft?.['受理人员'] ?? String(latest['受理人员'] ?? ''),
    '处理措施': draft?.['处理措施'] ?? String(latest['处理措施'] ?? ''),
  }
}

function cancelAccept() {
  saveDraft()
  accepting.value = false
}

async function submitAccept() {
  if (!acceptTarget) return
  saveDraft()
  const targetId = Number(acceptTarget.id)
  const measure = acceptForm.value['处理措施'].trim()
  if (!measure) {
    errorMessage.value = '请先填写处理措施后再提交受理'
    return
  }

  submitting.value = true
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${targetId}/actions`, {
      method: 'POST',
      body: JSON.stringify({
        values: {
          action: '受理诉求',
          '处理措施': measure,
          '受理人员': acceptForm.value['受理人员'].trim(),
        },
      }),
    })
    const payload = await response.json()
    if (!response.ok || !payload.ok) {
      // 保留 textarea 中已填写的处理措施，用户可以直接再次提交。
      throw new Error(payload.message || '受理提交失败，已保留填写内容，请重试')
    }
    clearDraft(targetId)
    detail.value = payload.entry as Row
    accepting.value = false
    acceptTarget = null
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '受理提交失败，已保留填写内容，请重试'
  } finally {
    submitting.value = false
  }
}

async function submitAction(action: string, row: Row) {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values: { action } }),
    })
    const payload = await response.json()
    if (!response.ok || !payload.ok) {
      throw new Error(payload.message || '诉求动作未生效，请稍后重试')
    }
    detail.value = payload.entry as Row
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '公众诉求操作失败'
  }
}

async function fetchRows(nextScope: 'todo' | 'all') {
  const params = new URLSearchParams()
  if (keyword.value.trim()) params.set('keyword', keyword.value.trim())
  if (statusFilter.value) params.set('status', statusFilter.value)
  params.set('scope', nextScope)
  params.set('size', '200')
  const response = await request(`${ENDPOINT}?${params.toString()}`)
  if (!response.ok) throw new Error('诉求记录列表读取失败')
  return await response.json() as { items?: Row[]; total?: number }
}

async function reload() {
  loading.value = true
  errorMessage.value = ''
  try {
    const [currentPayload, todoPayload, allPayload] = await Promise.all([
      fetchRows(scope.value),
      fetchRows('todo'),
      fetchRows('all'),
    ])
    rows.value = currentPayload.items ?? []
    total.value = currentPayload.total ?? rows.value.length
    todoCount.value = todoPayload.total ?? 0
    allCount.value = allPayload.total ?? 0
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '公众诉求列表读取失败'
  } finally {
    loading.value = false
  }
}

onMounted(reload)
</script>
