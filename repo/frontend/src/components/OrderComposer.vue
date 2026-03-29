<template>
  <article class="panel" v-if="selectedFolio">
    <p class="eyebrow">Guest commerce</p>
    <h2>Build cart and request quote</h2>
    <form class="form-grid" @submit.prevent="addOrUpdateCartItem">
      <label class="full-span">
        Offering
        <select v-model="itemDraft.catalog_key" @change="applyCatalogPreset">
          <option v-for="item in catalog" :key="item.key" :value="item.key">{{ item.label }}</option>
        </select>
      </label>
      <label>
        Item name
        <input v-model="itemDraft.name" required />
      </label>
      <label>
        Quantity
        <input v-model.number="itemDraft.quantity" min="1" required type="number" />
      </label>
      <label>
        Unit price
        <input v-model="itemDraft.unit_price" required type="number" min="0" step="0.01" readonly />
      </label>
      <label>
        Size/spec
        <input v-model="itemDraft.size" placeholder="regular" />
      </label>
      <label>
        Option specs (k=v,k=v)
        <input v-model="itemDraft.specs" placeholder="milk=oat,temp=hot" />
      </label>
      <label>
        Delivery slot label
        <input v-model="itemDraft.delivery_slot_label" placeholder="Breakfast rush" />
      </label>
      <div class="inline-actions full-span">
        <button class="ghost-button" type="button" @click="resetItemDraft">Clear item</button>
        <button class="primary-button" type="submit">{{ editingItemIndex === null ? 'Add item to cart' : 'Update cart item' }}</button>
      </div>
    </form>

    <div class="stack-list" style="margin-top: 12px;">
      <article class="stack-card" v-for="(item, index) in cartItems" :key="`${item.sku || item.name}-${index}`">
        <strong>{{ item.name }}</strong>
        <p>Qty {{ item.quantity }} · {{ item.size || 'standard' }} · ${{ Number(item.unit_price).toFixed(2) }} each</p>
        <p v-if="item.delivery_slot_label">Slot: {{ item.delivery_slot_label }}</p>
        <div class="inline-actions">
          <small class="hint">Line subtotal ${{ lineSubtotal(item).toFixed(2) }}</small>
          <div class="inline-actions">
            <button class="ghost-button" type="button" @click="editCartItem(index)">Edit</button>
            <button class="ghost-button" type="button" @click="removeCartItem(index)">Remove</button>
          </div>
        </div>
      </article>
      <p class="hint" v-if="!cartItems.length">Add at least one item to continue.</p>
    </div>

    <form class="form-grid" style="margin-top: 14px;" @submit.prevent="submitCart">
      <label>
        Payment method
        <select v-model="checkout.payment_method">
          <option value="direct_bill">direct_bill</option>
          <option value="card_present_manual">card_present_manual</option>
          <option value="gift_certificate">gift_certificate</option>
          <option value="cash">cash</option>
        </select>
      </label>
      <label>
        Packaging fee (auto)
        <input :value="packagingFeeAuto.toFixed(2)" type="number" min="0" step="0.01" readonly disabled />
      </label>
      <label class="checkbox-row">
        <input v-model="checkout.apply_service_charge" type="checkbox" />
        Apply optional 18% service charge
      </label>
      <label>
        Service fee
        <input v-model="checkout.service_fee" type="number" min="0" step="0.01" :disabled="checkout.apply_service_charge" />
      </label>
      <label>
        Delivery start
        <input v-model="checkout.delivery_start" type="datetime-local" required />
      </label>
      <label>
        Delivery end
        <input v-model="checkout.delivery_end" type="datetime-local" required />
      </label>
      <label class="full-span">
        Order note (max 250)
        <textarea v-model="checkout.order_note" maxlength="250" rows="3" placeholder="No peanuts; leave at room desk." />
      </label>
      <article class="stack-card full-span">
        <p>Cart subtotal: ${{ cartSubtotal.toFixed(2) }}</p>
        <p>Service fee: ${{ effectiveServiceFee.toFixed(2) }}</p>
        <p>Packaging fee: ${{ packagingFeeAuto.toFixed(2) }}</p>
        <strong>Quoted total before tax: ${{ projectedBeforeTax.toFixed(2) }}</strong>
      </article>
      <p class="hint full-span">Packaging fee policy: $2.50 is applied automatically when the cart includes food items.</p>
      <p v-if="validationError" class="message error full-span">{{ validationError }}</p>
      <button class="primary-button" :disabled="loading || !cartItems.length">{{ loading ? 'Posting...' : 'Confirm quote for cart' }}</button>
    </form>
    <p class="hint">Selected folio: room {{ selectedFolio.room_number }} · {{ selectedFolio.guest_name }}</p>
  </article>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'

function toLocalDateTimeInput(date) {
  const copy = new Date(date.getTime())
  copy.setMinutes(copy.getMinutes() - copy.getTimezoneOffset())
  return copy.toISOString().slice(0, 16)
}

const catalog = [
  { key: 'food_club_sandwich', sku: 'food_club_sandwich', label: 'Room Service - Club Sandwich', name: 'Club sandwich', unit_price: '14.00', size: 'regular', specs: 'sauce=light' },
  { key: 'spa_express_massage', sku: 'spa_express_massage', label: 'Spa Add-on - Express Massage', name: 'Express massage add-on', unit_price: '65.00', size: '30min', specs: 'therapist=any' },
  { key: 'late_checkout_2pm', sku: 'late_checkout_2pm', label: 'Late Checkout - 2 PM', name: 'Late checkout extension', unit_price: '45.00', size: '2pm', specs: 'floor=any' },
  { key: 'amenity_welcome_basket', sku: 'amenity_welcome_basket', label: 'Amenity - Welcome Basket', name: 'Welcome amenity basket', unit_price: '32.00', size: 'standard', specs: 'snacks=mixed' },
]

const props = defineProps({
  loading: { type: Boolean, default: false },
  selectedFolio: { type: Object, default: null },
})

const emit = defineEmits(['submit'])

const itemDraft = reactive({
  catalog_key: 'food_club_sandwich',
  sku: 'food_club_sandwich',
  name: 'Club sandwich',
  quantity: 1,
  unit_price: '14.00',
  size: 'regular',
  specs: 'sauce=light',
  delivery_slot_label: 'Standard service window',
})

const checkout = reactive({
  payment_method: 'direct_bill',
  apply_service_charge: true,
  service_fee: '0.00',
  delivery_start: toLocalDateTimeInput(new Date(Date.now() + 15 * 60 * 1000)),
  delivery_end: toLocalDateTimeInput(new Date(Date.now() + 45 * 60 * 1000)),
  order_note: '',
})

const cartItems = ref([])
const editingItemIndex = ref(null)
const validationError = ref('')

const cartSubtotal = computed(() => cartItems.value.reduce((sum, item) => sum + lineSubtotal(item), 0))
const hasFoodItem = computed(() => cartItems.value.some((item) => String(item.sku || '').startsWith('food_')))
const packagingFeeAuto = computed(() => (hasFoodItem.value ? 2.5 : 0))
const effectiveServiceFee = computed(() => {
  if (checkout.apply_service_charge) {
    return Number((cartSubtotal.value * 0.18).toFixed(2))
  }
  return Number(checkout.service_fee || 0)
})
const projectedBeforeTax = computed(() => cartSubtotal.value + packagingFeeAuto.value + effectiveServiceFee.value)

function applyCatalogPreset() {
  const preset = catalog.find((item) => item.key === itemDraft.catalog_key)
  if (!preset) {
    return
  }
  itemDraft.name = preset.name
  itemDraft.sku = preset.sku
  itemDraft.unit_price = preset.unit_price
  itemDraft.size = preset.size
  itemDraft.specs = preset.specs
}

function parseSpecs(specText) {
  return Object.fromEntries(
    String(specText || '')
      .split(',')
      .map((part) => part.trim())
      .filter(Boolean)
      .map((part) => {
        const [key, value] = part.split('=')
        return [key?.trim() || '', value?.trim() || '']
      })
      .filter(([key]) => key)
  )
}

function stringifySpecs(specObject) {
  return Object.entries(specObject || {})
    .map(([key, value]) => `${key}=${value}`)
    .join(',')
}

function lineSubtotal(item) {
  return Number(item.unit_price || 0) * Number(item.quantity || 0)
}

function buildDraftItem() {
  return {
    sku: itemDraft.sku || null,
    name: String(itemDraft.name || '').trim(),
    quantity: Number(itemDraft.quantity || 0),
    unit_price: Number(itemDraft.unit_price || 0).toFixed(2),
    size: String(itemDraft.size || '').trim(),
    specs: parseSpecs(itemDraft.specs),
    delivery_slot_label: String(itemDraft.delivery_slot_label || '').trim(),
  }
}

function addOrUpdateCartItem() {
  const nextItem = buildDraftItem()
  if (!nextItem.name || nextItem.quantity < 1) {
    return
  }
  if (editingItemIndex.value === null) {
    cartItems.value.push(nextItem)
  } else {
    cartItems.value.splice(editingItemIndex.value, 1, nextItem)
  }
  resetItemDraft()
}

function editCartItem(index) {
  const item = cartItems.value[index]
  if (!item) {
    return
  }
  editingItemIndex.value = index
  itemDraft.sku = item.sku || ''
  itemDraft.name = item.name
  itemDraft.quantity = item.quantity
  itemDraft.unit_price = Number(item.unit_price || 0).toFixed(2)
  itemDraft.size = item.size || ''
  itemDraft.specs = stringifySpecs(item.specs)
  itemDraft.delivery_slot_label = item.delivery_slot_label || ''
}

function removeCartItem(index) {
  cartItems.value.splice(index, 1)
  if (editingItemIndex.value === index) {
    resetItemDraft()
  }
}

function resetItemDraft() {
  editingItemIndex.value = null
  itemDraft.catalog_key = 'food_club_sandwich'
  applyCatalogPreset()
  itemDraft.quantity = 1
  itemDraft.delivery_slot_label = 'Standard service window'
}

function submitCart() {
  validationError.value = ''
  if (!cartItems.value.length) {
    return
  }
  const deliveryStartMs = new Date(checkout.delivery_start).getTime()
  const deliveryEndMs = new Date(checkout.delivery_end).getTime()
  if (Number.isNaN(deliveryStartMs) || Number.isNaN(deliveryEndMs)) {
    validationError.value = 'Delivery start and end are required.'
    return
  }
  if (deliveryEndMs <= deliveryStartMs) {
    validationError.value = 'Delivery end must be after delivery start.'
    return
  }
  if (deliveryStartMs < Date.now()) {
    validationError.value = 'Delivery start cannot be in the past.'
    return
  }
  emit('submit', {
    items: cartItems.value.map((item) => ({ ...item })),
    payment_method: checkout.payment_method,
    packaging_fee: packagingFeeAuto.value.toFixed(2),
    service_fee: effectiveServiceFee.value.toFixed(2),
    order_note: checkout.order_note || '',
    delivery_start: checkout.delivery_start,
    delivery_end: checkout.delivery_end,
  })
}
</script>
