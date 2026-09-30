<template>
  <section class="page" data-module="complaint">
    <header class="page-head">
      <div>
        <h2>公众诉求管理</h2>
        <p class="page-desc">维护诉求记录，围绕诉求编号、诉求来源、诉求内容、涉及管段做登记、筛选与状态流转。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记诉求记录</button>
        <button class="btn" type="button" @click="exportRows">导出公众诉求清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <div class="tabs" role="tablist">
      <button
        class="tab"
        :class="{ active: activeTab === 'list' }"
        type="button"
        role="tab"
        @click="activeTab = 'list'"
      >
        诉求列表
      </button>
      <button
        class="tab"
        :class="{ active: activeTab === 'todo' }"
        type="button"
        role="tab"
        @click="activeTab = 'todo'"
      >
        待办清单<span class="tab-count">{{ todoTotal }}</span>
      </button>
    </div>

    <template v-if="activeTab === 'list'">
      <form class="filter-bar" @submit.prevent="reload">
        <label class="filter-item">
          <span>诉求编号</span>
          <input v-model="filters.keyword" placeholder="按诉求编号检索" />
        </label>
        <label class="filter-item">
          <span>诉求状态</span>
          <select v-model="filters.status">
            <option value="">全部状态</option>
            <option v-for="status in statuses" :key="status" :value="status">{{ status }}</option>
          </select>
        </label>
        <button class="btn" type="submit">查询</button>
        <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
      </form>

      <table class="data-table">
        <thead>
          <tr>
            <th v-for="column in columns" :key="column">{{ column }}</th>
            <th>异常标记</th>
            <th>可执行动作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="String(row.id)" :class="{ 'row-abnormal': row.abnormal }">
            <td v-for="column in columns" :key="column">
              <template v-if="column === '诉求状态'">
                <span class="badge" :class="statusBadge(row.status)">{{ row.status }}</span>
              </template>
              <template v-else-if="column === '诉求来源'">
                <span v-if="row[column]">{{ row[column] }}</span>
                <span v-else class="warn-text">未登记来源</span>
              </template>
              <template v-else>{{ row[column] || '—' }}</template>
            </td>
            <td class="abnormal-cell">
              <template v-if="row.abnormal_reasons.length">
                <span v-for="reason in row.abnormal_reasons" :key="reason" class="badge danger">{{ reason }}</span>
              </template>
              <span v-else class="muted-text">正常</span>
            </td>
            <td class="row-actions">
              <button class="link" type="button" @click="openDetail(row)">查看详情</button>
              <button
                v-if="actionFor(row)"
                class="link"
                type="button"
                @click="runNext(row)"
              >
                {{ actionFor(row) }}<span v-if="draftIds.has(Number(row.id))" class="warn-text">（草稿）</span>
              </button>
              <span v-else class="muted-text">—</span>
            </td>
          </tr>
          <tr v-if="!rows.length">
            <td :colspan="columns.length + 2" class="empty-state">
              <span class="empty-title">当前范围没有符合条件的新诉求</span>
              <span class="empty-scope">{{ emptyScope }}</span>
            </td>
          </tr>
        </tbody>
      </table>

      <footer class="page-foot">
        <span>共 {{ total }} 条公众诉求记录{{ scopeSuffix }}</span>
        <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
      </footer>
    </template>

    <template v-else>
      <table class="data-table">
        <thead>
          <tr>
            <th>诉求编号</th>
            <th>诉求来源</th>
            <th>诉求内容</th>
            <th>办理期限</th>
            <th>状态</th>
            <th>回复时间</th>
            <th>可执行动作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in todoRows" :key="String(row.id)" :class="{ 'row-abnormal': row.abnormal }">
            <td>{{ row['诉求编号'] }}</td>
            <td>
              <span v-if="row['诉求来源']">{{ row['诉求来源'] }}</span>
              <span v-else class="warn-text">未登记来源</span>
            </td>
            <td>{{ row['诉求内容'] }}</td>
            <td>
              {{ row['办理期限'] || '—' }}
              <span v-if="row.overdue" class="badge danger">已超期</span>
            </td>
            <td><span class="badge" :class="statusBadge(row.status)">{{ row.status }}</span></td>
            <td>{{ row['回复时间'] || '—' }}</td>
            <td class="row-actions">
              <button class="link" type="button" @click="openDetail(row)">查看详情</button>
              <button class="link" type="button" @click="openAction('关闭诉求', row)">关闭诉求</button>
            </td>
          </tr>
          <tr v-if="!todoRows.length">
            <td colspan="7" class="empty-state">
              <span class="empty-title">待办清单为空</span>
              <span class="empty-scope">待办只汇聚「已回复、待跟进关闭」的诉求；当前诉求列表中没有已回复的记录。</span>
            </td>
          </tr>
        </tbody>
      </table>
      <footer class="page-foot">
        <span>待办 {{ todoTotal }} 条，与诉求列表中「已回复」状态的条数一致</span>
      </footer>
    </template>

    <!-- 受理 / 回复 弹窗：受理失败时保留已填内容并允许直接重试 -->
    <div v-if="actionModal.open" class="modal-mask" @mousedown.self="closeActionModal">
      <div class="modal" role="dialog" :aria-label="actionModal.action">
        <div class="modal-head">
          <h3>{{ actionModal.action }} · {{ actionModal.row?.['诉求编号'] }}</h3>
          <button class="modal-close" type="button" @click="closeActionModal">×</button>
        </div>

        <p v-if="draftRestored" class="warn-text">上次填写的内容尚未提交成功，已自动恢复，可继续修改后重试。</p>
        <p v-if="actionModal.row?.abnormal_reasons.length" class="warn-text">
          该诉求存在异常：{{ actionModal.row.abnormal_reasons.join('、') }}，请核实后再处理。
        </p>

        <div class="form-grid" v-if="actionModal.action === '受理诉求'">
          <label class="form-field">
            <span>受理人员 *</span>
            <input v-model="actionForm['受理人员']" placeholder="请输入受理人员" />
          </label>
          <label class="form-field">
            <span>办理期限</span>
            <input :value="actionModal.row?.['办理期限'] || ''" disabled />
          </label>
          <label class="form-field full">
            <span>处理措施 *</span>
            <textarea v-model="actionForm['处理措施']" placeholder="请填写拟采取的处理措施"></textarea>
          </label>
        </div>
        <div class="form-grid" v-else-if="actionModal.action === '提交回复'">
          <label class="form-field full">
            <span>回复内容 *</span>
            <textarea v-model="actionForm['回复内容']" placeholder="请填写向诉求人回复的内容"></textarea>
          </label>
          <div class="form-field full">
            <span class="muted-text">已登记处理措施：{{ actionModal.row?.['处理措施'] || '—' }}</span>
          </div>
        </div>
        <p v-else class="muted-text">确认该诉求已回复完成、可关闭归档？关闭后将不再出现在待办清单中。</p>

        <p v-if="actionError" class="error-text">{{ actionError }}</p>

        <div class="modal-foot">
          <button class="btn ghost" type="button" @click="closeActionModal">
            {{ actionModal.action === '关闭诉求' ? '取消' : '稍后处理（保留草稿）' }}
          </button>
          <button class="btn primary" type="button" :disabled="submitting" @click="submitAction">
            {{ submitting ? '提交中…' : `确认${actionModal.action}` }}
          </button>
        </div>
      </div>
    </div>

    <!-- 详情弹窗：状态直接取列表同一份后端数据，保证两处一致 -->
    <div v-if="detailModal.open" class="modal-mask" @mousedown.self="detailModal.open = false">
      <div class="modal" role="dialog" aria-label="诉求详情">
        <div class="modal-head">
          <h3>诉求详情 · {{ detailModal.row?.['诉求编号'] }}</h3>
          <button class="modal-close" type="button" @click="detailModal.open = false">×</button>
        </div>
        <p v-if="detailModal.error" class="error-text">{{ detailModal.error }}</p>
        <dl v-if="detailModal.row" class="detail-grid">
          <dt>诉求状态</dt>
          <dd><span class="badge" :class="statusBadge(detailModal.row.status)">{{ detailModal.row.status }}</span></dd>
          <dt>诉求来源</dt>
          <dd>
            <span v-if="detailModal.row['诉求来源']">{{ detailModal.row['诉求来源'] }}</span>
            <span v-else class="badge danger">诉求来源缺失</span>
          </dd>
          <dt>诉求内容</dt><dd>{{ detailModal.row['诉求内容'] }}</dd>
          <dt>涉及管段</dt><dd>{{ detailModal.row['涉及管段'] || '—' }}</dd>
          <dt>受理人员</dt><dd>{{ detailModal.row['受理人员'] || '尚未受理' }}</dd>
          <dt>处理措施</dt><dd>{{ detailModal.row['处理措施'] || '—' }}</dd>
          <dt>办理期限</dt>
          <dd>
            {{ detailModal.row['办理期限'] || '—' }}
            <span v-if="detailModal.row.overdue" class="badge danger">办理期限已过</span>
          </dd>
          <dt v-if="detailModal.row['回复内容']">回复内容</dt>
          <dd v-if="detailModal.row['回复内容']">{{ detailModal.row['回复内容'] }}（{{ detailModal.row['回复时间'] }}）</dd>
          <dt>异常说明</dt>
          <dd>
            <template v-if="detailModal.row.abnormal_reasons.length">
              <span v-for="reason in detailModal.row.abnormal_reasons" :key="reason" class="badge danger">{{ reason }}</span>
            </template>
            <span v-else>无异常</span>
          </dd>
        </dl>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'

import { request } from '@/api/client'

type Row = {
  id: number
  status: string
  pending: boolean
  abnormal: boolean
  abnormal_reasons: string[]
  overdue: boolean
  回复时间?: string
  [key: string]: string | number | boolean | string[] | undefined
}

type ActionName = '受理诉求' | '提交回复' | '关闭诉求'

const ENDPOINT = '/api/complaint'
const columns = ['诉求编号', '诉求来源', '诉求内容', '涉及管段', '受理人员', '处理措施', '办理期限', '诉求状态']
const statuses = ['待受理', '办理中', '已回复', '已关闭']
const NEXT_ACTIONS: Record<string, ActionName> = {
  待受理: '受理诉求',
  办理中: '提交回复',
  已回复: '关闭诉求',
}
const FORM_ACTIONS: ActionName[] = ['受理诉求', '提交回复']
const DRAFT_KEYS: Partial<Record<ActionName, string>> = {
  受理诉求: 'accept',
  提交回复: 'reply',
}

const rows = ref<Row[]>([])
const allRows = ref<Row[]>([])
const total = ref(0)
const todoRows = ref<Row[]>([])
const todoTotal = ref(0)
const errorMessage = ref('')
const activeTab = ref<'list' | 'todo'>('list')
const filters = reactive({ keyword: '', status: '' })

const stats = computed(() => {
  const count = (status: string) => allRows.value.filter((row) => row.status === status).length
  return [
    { label: '待受理诉求', value: count('待受理') },
    { label: '办理中诉求', value: count('办理中') },
    { label: '已回复待办', value: count('已回复') },
    { label: '本月关闭数', value: count('已关闭') },
  ]
})

const scopeSuffix = computed(() => {
  const parts: string[] = []
  if (filters.keyword.trim()) parts.push(`编号含「${filters.keyword.trim()}」`)
  if (filters.status) parts.push(`状态为「${filters.status}」`)
  return parts.length ? `（筛选范围：${parts.join('，')}）` : ''
})

const emptyScope = computed(() => {
  if (filters.keyword.trim() || filters.status) {
    return `当前筛选范围${scopeSuffix.value}内没有诉求，可放宽条件或重置后再查。`
  }
  return '当前展示全部状态、全部编号范围内的公众诉求；暂无新的待处理诉求。'
})

function statusBadge(status: string): string {
  if (status === '已回复') return 'info'
  if (status === '已关闭') return ''
  if (status === '办理中') return 'warn'
  return 'success'
}

function actionFor(row: Row): ActionName | null {
  return NEXT_ACTIONS[row.status] ?? null
}

function runNext(row: Row) {
  const action = actionFor(row)
  if (action) openAction(action, row)
}

// ---- 受理 / 回复 草稿：中断提交后重新进入同一条，能接着上次的内容处理 ----

const actionModal = reactive<{ open: boolean; action: ActionName; row: Row | null }>({
  open: false,
  action: '受理诉求',
  row: null,
})
const actionForm = ref<Record<string, string>>({})
const actionError = ref('')
const submitting = ref(false)
const draftRestored = ref(false)
const draftIds = ref<Set<number>>(new Set())

function draftKey(action: ActionName, id: number): string {
  return `complaint:draft:${DRAFT_KEYS[action] ?? 'unknown'}:${id}`
}

function scanDrafts() {
  const ids = new Set<number>()
  const prefix = 'complaint:draft:'
  for (let i = 0; i < window.localStorage.length; i += 1) {
    const key = window.localStorage.key(i)
    if (key?.startsWith(prefix)) {
      const id = Number(key.split(':').pop())
      if (!Number.isNaN(id)) ids.add(id)
    }
  }
  draftIds.value = ids
}

function saveDraft() {
  if (!actionModal.row || !FORM_ACTIONS.includes(actionModal.action)) return
  const values = Object.fromEntries(Object.entries(actionForm.value).filter(([, v]) => v.trim()))
  if (Object.keys(values).length) {
    window.localStorage.setItem(draftKey(actionModal.action, actionModal.row.id), JSON.stringify(values))
  } else {
    window.localStorage.removeItem(draftKey(actionModal.action, actionModal.row.id))
  }
  scanDrafts()
}

function clearDraft() {
  if (!actionModal.row || !FORM_ACTIONS.includes(actionModal.action)) return
  window.localStorage.removeItem(draftKey(actionModal.action, actionModal.row.id))
  scanDrafts()
}

watch(actionForm, () => {
  if (actionModal.open) saveDraft()
}, { deep: true })

function openAction(action: ActionName, row: Row) {
  actionModal.action = action
  actionModal.row = row
  actionError.value = ''
  draftRestored.value = false
  if (action === '受理诉求') {
    // 先带回该单已经登记的内容，再叠加本地未提交的草稿
    actionForm.value = { 受理人员: String(row['受理人员'] ?? ''), 处理措施: String(row['处理措施'] ?? '') }
  } else if (action === '提交回复') {
    actionForm.value = { 回复内容: '' }
  } else {
    actionForm.value = {}
  }
  if (FORM_ACTIONS.includes(action)) {
    const saved = window.localStorage.getItem(draftKey(action, row.id))
    if (saved) {
      try {
        Object.assign(actionForm.value, JSON.parse(saved) as Record<string, string>)
        draftRestored.value = true
      } catch {
        window.localStorage.removeItem(draftKey(action, row.id))
      }
    }
  }
  actionModal.open = true
}

function closeActionModal() {
  // 关闭即中断：受理/回复草稿已随输入实时保存，下次进入这条仍可继续
  saveDraft()
  actionModal.open = false
  actionModal.row = null
  actionForm.value = {}
  actionError.value = ''
}

async function submitAction() {
  if (!actionModal.row) return
  actionError.value = ''
  submitting.value = true
  try {
    const response = await request(`${ENDPOINT}/${actionModal.row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values: { action: actionModal.action, ...actionForm.value } }),
    })
    let payload: { ok: boolean; message: string } | null = null
    try {
      payload = (await response.json()) as { ok: boolean; message: string }
    } catch {
      payload = null
    }
    if (!response.ok || !payload?.ok) {
      // 失败时不关闭弹窗、不清表单，保留已填处理措施供用户修改后重试
      actionError.value = payload?.message || `${actionModal.action}未生效，请检查网络后重试（已填内容已保留）`
      return
    }
    clearDraft()
    actionModal.open = false
    actionModal.row = null
    await reload()
  } catch (error) {
    actionError.value = error instanceof Error ? error.message : '提交失败，请稍后重试（已填内容已保留）'
  } finally {
    submitting.value = false
  }
}

// ---- 详情 ----

const detailModal = reactive<{ open: boolean; row: Row | null; error: string }>({
  open: false,
  row: null,
  error: '',
})

async function openDetail(row: Row) {
  detailModal.open = true
  detailModal.row = null
  detailModal.error = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}`)
    if (!response.ok) throw new Error('诉求详情读取失败')
    detailModal.row = (await response.json()) as Row
  } catch (error) {
    detailModal.error = error instanceof Error ? error.message : '诉求详情读取失败'
  }
}

// ---- 列表读取 ----

async function fetchJson(path: string): Promise<{ items: Row[]; total: number }> {
  const response = await request(path)
  if (!response.ok) throw new Error('诉求记录列表读取失败')
  return (await response.json()) as { items: Row[]; total: number }
}

function resetFilters() {
  filters.keyword = ''
  filters.status = ''
  void reload()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function openCreate() {
  errorMessage.value = '诉求记录登记入口尚未接入审批流'
}

async function reload() {
  errorMessage.value = ''
  const params = new URLSearchParams()
  if (filters.keyword.trim()) params.set('keyword', filters.keyword.trim())
  if (filters.status) params.set('status', filters.status)
  params.set('size', '200')
  const query = params.toString()
  try {
    const [filtered, unfiltered, todo] = await Promise.all([
      fetchJson(`${ENDPOINT}?${query}`),
      fetchJson(`${ENDPOINT}?size=200`),
      fetchJson(`${ENDPOINT}/todo`),
    ])
    rows.value = filtered.items
    total.value = filtered.total
    allRows.value = unfiltered.items
    todoRows.value = todo.items
    todoTotal.value = todo.total
    scanDrafts()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '公众诉求列表读取失败'
  }
}

onMounted(reload)
</script>

<style scoped>
.row-abnormal { background: #fffbf5; }
.row-abnormal:hover { background: #fef6e7; }
.filter-item select { padding: 6px 8px; border: 1px solid var(--border); border-radius: 6px; background: #fff; }
</style>
