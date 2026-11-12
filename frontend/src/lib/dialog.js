export function focusDialog(node) {
  const previousFocus = document.activeElement
  node.focus({ preventScroll: true })

  function onKeydown(event) {
    if (event.key !== 'Tab') return
    const controls = [...node.querySelectorAll(
      'button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])',
    )].filter((element) => element.getClientRects().length > 0)
    const first = controls[0]
    const last = controls.at(-1)

    if (!first) {
      event.preventDefault()
      node.focus()
    } else if (event.shiftKey && (document.activeElement === first || document.activeElement === node)) {
      event.preventDefault()
      last.focus()
    } else if (!event.shiftKey && (document.activeElement === last || document.activeElement === node)) {
      event.preventDefault()
      first.focus()
    }
  }

  node.addEventListener('keydown', onKeydown)
  return {
    destroy() {
      node.removeEventListener('keydown', onKeydown)
      if (previousFocus?.isConnected) previousFocus.focus({ preventScroll: true })
    },
  }
}
