export function getSignalId(feature, index) {
  const id = feature?.properties?.tls_id ?? feature?.properties?.name
  return typeof id === 'string' && id.trim() ? id : `signal-${index}`
}
