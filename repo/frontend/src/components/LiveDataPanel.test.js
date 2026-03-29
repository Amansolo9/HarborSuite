import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import LiveDataPanel from './LiveDataPanel.vue'

describe('LiveDataPanel', () => {
  it('shows loading states for folios and orders', () => {
    const wrapper = mount(LiveDataPanel, {
      props: {
        folios: [],
        orders: [],
        loading: true,
        formatDate: (value) => String(value),
      },
    })

    expect(wrapper.text()).toContain('Loading folios...')
    expect(wrapper.text()).toContain('Loading orders...')
  })

  it('shows empty states when data is absent and not loading', () => {
    const wrapper = mount(LiveDataPanel, {
      props: {
        folios: [],
        orders: [],
        loading: false,
        formatDate: (value) => String(value),
      },
    })

    expect(wrapper.text()).toContain('No folios available.')
    expect(wrapper.text()).toContain('No orders available.')
  })
})
