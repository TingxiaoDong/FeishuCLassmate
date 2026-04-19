/**
 * Minimal browser-side Feishu Bitable reader for the dashboard.
 * Requires the caller to supply a valid tenant_access_token.
 */

export async function fetchBitableRecords(appToken, tableId, opts = {}) {
  const { token, filter, pageSize = 100 } = opts;
  if (!token) throw new Error('fetchBitableRecords: token missing');
  const params = new URLSearchParams({ page_size: String(pageSize) });
  if (filter) params.set('filter', filter);
  const url = `https://open.feishu.cn/open-apis/bitable/v1/apps/${appToken}/tables/${tableId}/records?${params}`;

  const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new Error(`bitable list ${tableId}: HTTP ${res.status}`);
  const data = await res.json();
  if (data.code !== 0) throw new Error(`bitable list ${tableId}: ${data.msg}`);

  return (data.data?.items ?? []).map((r) => ({ record_id: r.record_id, ...r.fields }));
}
