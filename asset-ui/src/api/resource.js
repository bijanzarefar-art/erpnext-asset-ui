// frappe-ui's createResource({ auto: true }) calls out.fetch() at the end of
// createResource, outside Vue's async error handling. fetch() is async and frappe-ui
// rethrows after recording the error, so any failed auto load (a 403 on an asset
// outside the caller's User Permission, for example) escaped as an uncaught promise
// rejection. The views already read the outcome from `resource.error`.

export function autoResource(createResource, options) {
  const resource = createResource({ ...options, auto: false })
  if (options.auto) {
    // Swallow only the promise; `error` still carries the failure to the component.
    // createListResource's fetch() returns nothing, so guard before calling .catch.
    const pending = resource.fetch()
    if (pending && typeof pending.catch === 'function') pending.catch(() => {})
  }
  return resource
}
