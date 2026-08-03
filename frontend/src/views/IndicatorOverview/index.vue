<script setup lang="ts">
import { ref, onMounted, computed, type Ref } from 'vue'
import { getWmsSummary, getWmsClaim, getErpClaim } from '@/api/modules/theme1'
import type { WmsClaimSplit, WmsClaimRange, ErpClaimSplit, ErpClaimRange } from '@/api/modules/theme1'
import { getStructure, getByProject, getByPurchaser } from '@/api/modules/theme2'
import { getTimeIndicators, getAgeLayers } from '@/api/modules/theme3'
import { getTopUnclaimedAmount, getTopUnclaimedQuantity } from '@/api/modules/theme4'
import { getTopClaimedAmount, getTopClaimedQuantity } from '@/api/modules/dashboard'
import { formatDays } from '@/utils/format'

const loading = ref(false)
const errorMsg = ref('')

const summary = ref<any>(null)
const claim = ref<WmsClaimSplit | null>(null)
const erpClaim = ref<ErpClaimSplit | null>(null)
const structure = ref<any>(null)
const timeIndicators = ref<any>(null)
const projectIndicators = ref<any[]>([])
const purchaserIndicators = ref<any[]>([])
const topUnclaimedAmt = ref<any[]>([])
const topUnclaimedQty = ref<any[]>([])
const topClaimedAmt = ref<any[]>([])
const topClaimedQty = ref<any[]>([])
const ageLayersSample = ref<any>(null)

async function loadAll() {
  loading.value = true
  errorMsg.value = ''
  try {
    const [s, c, ec, st, ti, proj, purch, tua, tuq, tca, tcq, al] = await Promise.all([
      getWmsSummary(), getWmsClaim(), getErpClaim(), getStructure(), getTimeIndicators(),
      getByProject(), getByPurchaser(),
      getTopUnclaimedAmount(10), getTopUnclaimedQuantity(10),
      getTopClaimedAmount(10), getTopClaimedQuantity(10),
      getAgeLayers({ min_amount: 100000, min_age: 365 }),
    ])
    summary.value = s; claim.value = c; erpClaim.value = ec; structure.value = st
    timeIndicators.value = ti; projectIndicators.value = proj
    purchaserIndicators.value = purch; topUnclaimedAmt.value = tua
    topUnclaimedQty.value = tuq; topClaimedAmt.value = tca
    topClaimedQty.value = tcq; ageLayersSample.value = al
  } catch (e: any) {
    errorMsg.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

function fmtWan(v: number) { return (v / 10000).toFixed(2) }
function fmtPct(v: number) { return v?.toFixed(2) + '%' }
function truncateText(text: string, maxLen = 20): string {
  if (!text) return ''
  return text.length > maxLen ? text.slice(0, maxLen) + '…' : text
}
function claimRange(type: 'year' | 'all'): WmsClaimRange {
  return claim.value?.[type] ?? {
    claim_rate_amount: 0,
    claim_rate_quantity: 0,
    unclaimed_amount: 0,
    unclaimed_amount_ratio: 0,
    total_inbound_amount: 0,
    total_claimed_amount: 0,
    total_inbound_quantity: 0,
    total_claimed_quantity: 0,
  }
}
function erpClaimRange(type: 'year' | 'all'): ErpClaimRange {
  return erpClaim.value?.[type] ?? {
    claim_rate_amount: 0, claim_rate_quantity: 0,
    unclaimed_amount: 0, unclaimed_amount_ratio: 0,
    total_inbound_amount: 0, total_outbound_amount: 0,
    total_inbound_quantity: 0, total_outbound_quantity: 0,
  }
}

// ===== 表格排序 =====
const projectSortKey = ref('')
const projectSortDir = ref<'asc' | 'desc'>('desc')
const purchaserSortKey = ref('')
const purchaserSortDir = ref<'asc' | 'desc'>('desc')

type SortDir = 'asc' | 'desc'
function applySort(keyRef: Ref<string>, dirRef: Ref<SortDir>, key: string) {
  if (keyRef.value !== key) { keyRef.value = key; dirRef.value = 'desc' }
  else if (dirRef.value === 'desc') { dirRef.value = 'asc' }
  else { keyRef.value = ''; dirRef.value = 'desc' }
}
function toggleProjectSort(key: string) { applySort(projectSortKey, projectSortDir, key) }
function togglePurchaserSort(key: string) { applySort(purchaserSortKey, purchaserSortDir, key) }

function sortData<T extends Record<string, any>>(data: T[], key: string, dir: SortDir): T[] {
  if (!key) return data
  const sorted = [...data].sort((a, b) => {
    const va = a[key] ?? ''
    const vb = b[key] ?? ''
    let cmp: number
    if (typeof va === 'string') cmp = va.localeCompare(vb, 'zh-CN')
    else cmp = Number(va) - Number(vb)
    return dir === 'asc' ? cmp : -cmp
  })
  return sorted
}

const sortedProjectIndicators = computed(() => {
  const filtered = projectIndicators.value.filter(p => p.project_code)
  return sortData(filtered, projectSortKey.value, projectSortDir.value)
})
const sortedPurchaserIndicators = computed(() =>
  sortData(purchaserIndicators.value, purchaserSortKey.value, purchaserSortDir.value),
)

// 从 age_structure 计算长库龄各段金额（万元）
const ageAmounts = computed(() => {
  const segs = timeIndicators.value?.age_structure || []
  const findAmt = (range: string) => segs.find((s: any) => s.range === range)?.amount ?? 0
  const aged1y = findAmt('1~3年') + findAmt('3~5年') + findAmt('≥5年')
  const aged3y = findAmt('3~5年') + findAmt('≥5年')
  const aged5y = findAmt('≥5年')
  return { aged1y: (aged1y / 10000).toFixed(2), aged3y: (aged3y / 10000).toFixed(2), aged5y: (aged5y / 10000).toFixed(2) }
})

onMounted(loadAll)
</script>

<template>
  <div v-loading="loading" class="overview-page">
    <div v-if="errorMsg" class="error-banner">❌ {{ errorMsg }}</div>
    <template v-if="!errorMsg && summary">
      <h2>📋 指标一览</h2>

      <!-- (一) 库存领用指标 -->
      <section>
        <h3>（一）库存领用指标</h3>
        <div class="kpi-section-hint" v-if="erpClaim">
          数据来源：ERP (erp_catalog_mb51) | 当年 {{ erpClaim.year_start }} ~ {{ erpClaim.year_end }}
        </div>
        <div class="kpi-cards">
          <div class="kpi-card">
            <div class="kpi-label">1a. 当年采购领用率（金额）</div>
            <div class="kpi-formula">= {{ erpClaimRange('year').total_outbound_amount?.toFixed(0) || 0 }}万 / {{ erpClaimRange('year').total_inbound_amount?.toFixed(0) || 0 }}万</div>
            <div class="kpi-value">{{ fmtPct(erpClaimRange('year').claim_rate_amount) }}</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">1b. 历史采购领用率（金额）</div>
            <div class="kpi-formula">= {{ erpClaimRange('all').total_outbound_amount?.toFixed(0) || 0 }}万 / {{ erpClaimRange('all').total_inbound_amount?.toFixed(0) || 0 }}万</div>
            <div class="kpi-value">{{ fmtPct(erpClaimRange('all').claim_rate_amount) }}</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">2a. 当年未领用采购金额</div>
            <div class="kpi-formula">= 当年入库金额 - 当年出库金额</div>
            <div class="kpi-value">{{ erpClaimRange('year').unclaimed_amount?.toLocaleString() }} 万元</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">2b. 全部未领用采购金额</div>
            <div class="kpi-formula">= 全部入库金额 - 全部出库金额</div>
            <div class="kpi-value">{{ erpClaimRange('all').unclaimed_amount?.toLocaleString() }} 万元</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">3a. 当年未领用采购占比（金额）</div>
            <div class="kpi-formula">= 当年未领用金额 / 当年入库金额</div>
            <div class="kpi-value">{{ fmtPct(erpClaimRange('year').unclaimed_amount_ratio) }}</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">3b. 全部未领用采购占比（金额）</div>
            <div class="kpi-formula">= 全部未领用金额 / 全部入库金额</div>
            <div class="kpi-value">{{ fmtPct(erpClaimRange('all').unclaimed_amount_ratio) }}</div>
          </div>
        </div>
      </section>

      <!-- (二) 库存结构指标 -->
      <section>
        <h3>（二）库存结构指标</h3>
        <div class="kpi-cards">
          <div class="kpi-card"><div class="kpi-label">4a. 当年库存金额</div><div class="kpi-value">{{ structure?.current_year_inventory_amount?.toFixed(2) }} 万元</div></div>
          <div class="kpi-card"><div class="kpi-label">4b. 所有库存金额</div><div class="kpi-value">{{ structure?.current_inventory_amount?.toFixed(2) }} 万元</div></div>
          <!-- <div class="kpi-card"><div class="kpi-label">6. 当前库存数量</div><div class="kpi-value">{{ fmtNum(structure?.current_inventory_quantity) }}</div></div> -->
        </div>
        <h4>5. 项目库存占比 TOP 10</h4>
        <table class="data-table" v-if="structure?.project_ratios?.length">
          <thead><tr><th>项目</th><th class="num">库存金额(万)</th><th class="num">占比</th></tr></thead>
          <tbody><tr v-for="p in structure.project_ratios.filter(p => p.project_code).slice(0,10)" :key="p.project_code"><td>{{ p.project_name || p.project_code }}</td><td class="num">{{ fmtWan(p.inventory_amount) }}</td><td class="num">{{ (p.ratio * 100).toFixed(2) }}%</td></tr></tbody>
        </table>
        <h4>6. 提报人库存占比 TOP 10</h4>
        <table class="data-table" v-if="structure?.purchaser_ratios?.length">
          <thead><tr><th>提报人</th><th class="num">库存金额(万)</th><th class="num">占比</th></tr></thead>
          <tbody><tr v-for="p in structure.purchaser_ratios.slice(0,10)" :key="p.purchaser_name"><td>{{ p.purchaser_name }}</td><td class="num">{{ fmtWan(p.inventory_amount) }}</td><td class="num">{{ (p.ratio * 100).toFixed(2) }}%</td></tr></tbody>
        </table>
      </section>

      <!-- (三) 库存时间指标 -->
      <section>
        <h3>（三）库存时间指标</h3>
        <div class="kpi-cards">
          <div class="kpi-card"><div class="kpi-label">7. 长库龄库存金额占比（≥1年）</div><div class="kpi-value">{{ (timeIndicators?.aged_ratio_1y * 100).toFixed(1) }}%</div></div>
          <div class="kpi-card"><div class="kpi-label">8. 库龄 ≥ 1 年库存金额</div><div class="kpi-value">{{ ageAmounts.aged1y }} 万元</div></div>
          <div class="kpi-card"><div class="kpi-label">9. 库龄 ≥ 3 年库存金额</div><div class="kpi-value">{{ ageAmounts.aged3y }} 万元</div></div>
          <div class="kpi-card"><div class="kpi-label">10. 平均库龄（金额加权）</div><div class="kpi-formula">= Σ（库存金额 × 库龄） / 总库存金额</div><div class="kpi-value">{{ timeIndicators?.avg_age_weighted_days }} 天</div></div>
        </div>
        <h4>11. 库龄结构占比</h4>
        <div class="age-bars" v-if="timeIndicators?.age_structure">
          <div v-for="seg in timeIndicators.age_structure" :key="seg.range" class="age-bar">
            <span class="age-range">{{ seg.range }}</span><div class="age-track"><div class="age-fill" :style="{ width: Math.max(seg.ratio*100,1)+'%' }"></div></div>
            <span class="age-pct">{{ (seg.ratio*100).toFixed(2) }}%</span><span class="age-count">{{ seg.count }}笔</span>
          </div>
        </div>
        <h4>12. 库龄分层统计（库存 &gt; 10万 且 库龄 &gt; 1年）</h4>
        <table class="data-table" v-if="ageLayersSample?.length">
          <thead><tr><th>物料编码</th><th>物资名称</th><th>项目名称</th><th>批次</th><th class="num">库存金额(万)</th><th class="num">数量</th><th class="num">库龄(天)</th></tr></thead>
          <tbody><tr v-for="item in ageLayersSample.slice(0,10)" :key="item.id">
            <td><code>{{ item.material_code }}</code></td>
            <td>
              <el-tooltip :content="item.material_name || ''" placement="top" :disabled="(item.material_name || '').length <= 20">
                <span>{{ truncateText(item.material_name) }}</span>
              </el-tooltip>
            </td>
            <td>
              <el-tooltip :content="item.project_name || item.project_code || ''" placement="top" :disabled="(item.project_name || item.project_code || '').length <= 20">
                <span>{{ truncateText(item.project_name || item.project_code) }}</span>
              </el-tooltip>
            </td>
            <td>{{ item.batch_code }}</td>
            <td class="num">{{ fmtWan(item.inventory_amount) }}</td>
            <td class="num">{{ item.current_quantity }}</td>
            <td class="num">{{ formatDays(item.age_days) }}</td>
          </tr></tbody>
        </table>
      </section>

      <!-- (四) 项目维度指标 -->
      <section>
        <h3>（四）项目维度指标 <span class="sort-hint">按未消耗金额降序</span></h3>
        <table class="data-table" v-if="projectIndicators.length">
          <thead><tr>
            <th class="sortable" @click="toggleProjectSort('project_name')">项目<span class="sort-arrow" v-if="projectSortKey === 'project_name'">{{ projectSortDir === 'asc' ? ' ▲' : ' ▼' }}</span></th>
            <th class="num sortable" @click="toggleProjectSort('inbound_amount')">入库(万)<span class="sort-arrow" v-if="projectSortKey === 'inbound_amount'">{{ projectSortDir === 'asc' ? ' ▲' : ' ▼' }}</span></th>
            <th class="num sortable" @click="toggleProjectSort('claimed_amount')">领用(万)<span class="sort-arrow" v-if="projectSortKey === 'claimed_amount'">{{ projectSortDir === 'asc' ? ' ▲' : ' ▼' }}</span></th>
            <th class="num sortable" @click="toggleProjectSort('unclaimed_amount')">未消耗(万)<span class="sort-arrow" v-if="projectSortKey === 'unclaimed_amount'">{{ projectSortDir === 'asc' ? ' ▲' : ' ▼' }}</span></th>
            <th class="num sortable" @click="toggleProjectSort('claim_rate')">领用率<span class="sort-arrow" v-if="projectSortKey === 'claim_rate'">{{ projectSortDir === 'asc' ? ' ▲' : ' ▼' }}</span></th>
            <th class="num sortable" @click="toggleProjectSort('avg_age_days')">平均库龄<span class="sort-arrow" v-if="projectSortKey === 'avg_age_days'">{{ projectSortDir === 'asc' ? ' ▲' : ' ▼' }}</span></th>
          </tr></thead>
          <tbody><tr v-for="p in sortedProjectIndicators.slice(0,15)" :key="p.project_code"><td>{{ p.project_name || p.project_code }}</td><td class="num">{{ fmtWan(p.inbound_amount) }}</td><td class="num">{{ fmtWan(p.claimed_amount) }}</td><td class="num">{{ fmtWan(p.unclaimed_amount) }}</td><td class="num">{{ p.claim_rate }}%</td><td class="num">{{ formatDays(p.avg_age_days) }}</td></tr></tbody>
        </table>
      </section>

      <!-- (五) 采购人维度指标 -->
      <section>
        <h3>（五）采购人维度指标 <span class="sort-hint">按未消耗金额降序</span></h3>
        <table class="data-table" v-if="purchaserIndicators.length">
          <thead><tr>
            <th class="sortable" @click="togglePurchaserSort('purchaser_name')">采购人<span class="sort-arrow" v-if="purchaserSortKey === 'purchaser_name'">{{ purchaserSortDir === 'asc' ? ' ▲' : ' ▼' }}</span></th>
            <th class="num sortable" @click="togglePurchaserSort('inbound_amount')">入库(万)<span class="sort-arrow" v-if="purchaserSortKey === 'inbound_amount'">{{ purchaserSortDir === 'asc' ? ' ▲' : ' ▼' }}</span></th>
            <th class="num sortable" @click="togglePurchaserSort('claimed_amount')">领用(万)<span class="sort-arrow" v-if="purchaserSortKey === 'claimed_amount'">{{ purchaserSortDir === 'asc' ? ' ▲' : ' ▼' }}</span></th>
            <th class="num sortable" @click="togglePurchaserSort('unclaimed_amount')">未消耗(万)<span class="sort-arrow" v-if="purchaserSortKey === 'unclaimed_amount'">{{ purchaserSortDir === 'asc' ? ' ▲' : ' ▼' }}</span></th>
            <th class="num sortable" @click="togglePurchaserSort('claim_rate')">领用率<span class="sort-arrow" v-if="purchaserSortKey === 'claim_rate'">{{ purchaserSortDir === 'asc' ? ' ▲' : ' ▼' }}</span></th>
            <th class="num sortable" @click="togglePurchaserSort('avg_age_days')">平均库龄<span class="sort-arrow" v-if="purchaserSortKey === 'avg_age_days'">{{ purchaserSortDir === 'asc' ? ' ▲' : ' ▼' }}</span></th>
          </tr></thead>
          <tbody><tr v-for="p in sortedPurchaserIndicators.slice(0,15)" :key="p.purchaser_name"><td>{{ p.purchaser_name }}</td><td class="num">{{ fmtWan(p.inbound_amount) }}</td><td class="num">{{ fmtWan(p.claimed_amount) }}</td><td class="num">{{ fmtWan(p.unclaimed_amount) }}</td><td class="num">{{ p.claim_rate }}%</td><td class="num">{{ formatDays(p.avg_age_days) }}</td></tr></tbody>
        </table>
      </section>

      <!-- (六) TOP类指标 -->
      <section>
        <h3>（六）TOP 类指标</h3>
        <h4>13. 未领用库存 TOP10（金额）</h4>
        <table class="data-table" v-if="topUnclaimedAmt.length">
          <thead><tr><th>物料编码</th><th>物料名称</th><th class="num">库存金额(万)</th><th class="num">库龄(天)</th><th>项目</th><th>采购人</th></tr></thead>
          <tbody><tr v-for="item in topUnclaimedAmt" :key="item.material_code"><td><code>{{ item.material_code }}</code></td><td>{{ item.material_name }}</td><td class="num">{{ fmtWan(item.inventory_amount) }}</td><td class="num">{{ formatDays(item.age_days) }}</td><td>{{ item.owner_project_name || '-' }}</td><td>{{ item.purchaser_name || '-' }}</td></tr></tbody>
        </table>
        <h4>14. 未领用库存 TOP10（数量）</h4>
        <table class="data-table" v-if="topUnclaimedQty.length">
          <thead><tr><th>物料编码</th><th>物料名称</th><th class="num">库存数量</th><th class="num">库存金额(万)</th><th class="num">库龄(天)</th></tr></thead>
          <tbody><tr v-for="item in topUnclaimedQty" :key="item.material_code"><td><code>{{ item.material_code }}</code></td><td>{{ item.material_name }}</td><td class="num">{{ item.current_quantity }} {{ item.unit }}</td><td class="num">{{ fmtWan(item.inventory_amount) }}</td><td class="num">{{ formatDays(item.age_days) }}</td></tr></tbody>
        </table>
        <h4>15. 领用 TOP10（金额）</h4>
        <table class="data-table" v-if="topClaimedAmt.length">
          <thead><tr><th>物料编码</th><th>物料名称</th><th class="num">领用金额(万)</th><th class="num">入库金额(万)</th><th>入库日期</th></tr></thead>
          <tbody><tr v-for="item in topClaimedAmt" :key="item.material_code"><td><code>{{ item.material_code }}</code></td><td>{{ item.material_name }}</td><td class="num">{{ fmtWan(item.claimed_amount) }}</td><td class="num">{{ fmtWan(item.inbound_amount) }}</td><td>{{ item.inbound_date?.slice(0,10) }}</td></tr></tbody>
        </table>
        <h4>16. 领用 TOP10（数量）</h4>
        <table class="data-table" v-if="topClaimedQty.length">
          <thead><tr><th>物料编码</th><th>物料名称</th><th class="num">领用数量</th><th class="num">入库数量</th><th>入库日期</th></tr></thead>
          <tbody><tr v-for="item in topClaimedQty" :key="item.material_code"><td><code>{{ item.material_code }}</code></td><td>{{ item.material_name }}</td><td class="num">{{ item.claimed_quantity?.toLocaleString() }}</td><td class="num">{{ item.inbound_quantity?.toLocaleString() }}</td><td>{{ item.inbound_date?.slice(0,10) }}</td></tr></tbody>
        </table>
      </section>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.overview-page {
  padding: 0 0 32px; color: #1e293b;
  h2 { font-size: 22px; margin-bottom: 24px; }
  h3 { font-size: 17px; font-weight: 600; margin: 28px 0 16px; padding-bottom: 8px; border-bottom: 2px solid #e2e8f0; }
  h4 { font-size: 14px; color: #475569; margin: 16px 0 10px; }
}
.error-banner { color: #dc2626; padding: 16px; background: #fef2f2; border-radius: 8px; margin-bottom: 16px; }

.kpi-section-hint { font-size: 12px; color: #64748b; margin: -8px 0 12px; }
.sort-hint { font-size: 12px; font-weight: 400; color: #94a3b8; margin-left: 8px; }
.kpi-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; margin-bottom: 8px; }
.kpi-card { background: #fff; border-radius: 8px; padding: 16px 20px; border: 1px solid #e2e8f0;
  .kpi-label { font-size: 13px; color: #64748b; }
  .kpi-formula { font-size: 11px; color: #94a3b8; margin: 2px 0 6px; }
  .kpi-value { font-size: 24px; font-weight: 700; color: #3b82f6; }
}

.age-bars { display: flex; flex-direction: column; gap: 8px; margin-bottom: 16px; }
.age-bar { display: flex; align-items: center; gap: 10px; }
.age-range { width: 60px; font-size: 12px; color: #64748b; text-align: right; flex-shrink: 0; }
.age-track { flex: 1; height: 20px; background: #f1f5f9; border-radius: 4px; overflow: hidden; }
.age-fill { height: 100%; background: #3b82f6; border-radius: 4px; min-width: 2px; }
.age-pct { width: 50px; font-size: 13px; font-weight: 600; }
.age-count { width: 40px; font-size: 11px; color: #94a3b8; }

.data-table { width: 100%; border-collapse: collapse; font-size: 13px;
  th { background: #f8fafc; padding: 8px 12px; font-weight: 600; color: #64748b; font-size: 12px; border-bottom: 2px solid #e2e8f0; }
  td { padding: 7px 12px; border-bottom: 1px solid #f1f5f9; color: #334155; }
  th, td { text-align: left; }
  .num { text-align: right; font-variant-numeric: tabular-nums; }
  code { font-size: 11px; background: #f1f5f9; padding: 2px 5px; border-radius: 3px; }
  tbody tr:hover { background: #f8fafc; }
}
.sortable { cursor: pointer; user-select: none; white-space: nowrap;
  &:hover { color: #3b82f6; background: #eff6ff; }
}
.sort-arrow { font-size: 10px; color: #3b82f6; }
</style>
