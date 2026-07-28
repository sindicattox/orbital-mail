export const mailStyles = `
  :host {
    display: block;
    color: var(--orbital-text, #172033);
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }
  * { box-sizing: border-box; }
  [hidden] { display: none !important; }
  .page-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; margin-bottom: 1.25rem; }
  .page-head h1 { margin: 0; font-size: 1.55rem; }
  .page-head p { margin: .35rem 0 0; color: var(--orbital-muted-text, #667085); }
  .button { border: 0; border-radius: .55rem; background: var(--orbital-primary, #175cd3); color: #fff; padding: .7rem 1rem; font: inherit; font-weight: 700; text-decoration: none; cursor: pointer; }
  .button.secondary { background: var(--orbital-surface, #fff); color: var(--orbital-text, #344054); border: 1px solid var(--orbital-border, #cfd8e5); }
  .button.danger { color: var(--orbital-danger, #b42318); }
  .button:disabled, button:disabled { opacity: .6; cursor: not-allowed; }
  .table-wrap { background: var(--orbital-surface, #fff); border: 1px solid var(--orbital-border, #dbe3ee); border-radius: .8rem; overflow: auto; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: .85rem 1rem; border-bottom: 1px solid var(--orbital-border, #eaecf0); font-size: .9rem; }
  th { background: var(--orbital-table-head, #f9fafb); color: var(--orbital-muted-text, #475467); }
  tr:last-child td { border-bottom: 0; }
  .empty { text-align: center; padding: 3rem 1rem; color: var(--orbital-muted-text, #667085); }
  .badge { display: inline-flex; padding: .25rem .55rem; border-radius: 999px; background: var(--orbital-muted-surface, #f2f4f7); font-size: .78rem; }
  .actions { white-space: nowrap; min-width: 250px; }
  .icon-button { display: inline-flex; border: 0; background: transparent; color: var(--orbital-primary, #175cd3); text-decoration: none; font: inherit; font-weight: 700; cursor: pointer; padding: .3rem; }
  .icon-button.danger { color: var(--orbital-danger, #b42318); }
  td small { display: block; color: var(--orbital-muted-text, #667085); margin-top: .2rem; }
  .message { border-radius: .65rem; padding: .8rem 1rem; margin-bottom: 1rem; }
  .message.error { background: #fef3f2; border: 1px solid #fecdca; color: #b42318; }
  .message.success { background: #ecfdf3; border: 1px solid #abefc6; color: #067647; }
  .queue-dialog { width: min(560px, calc(100vw - 32px)); padding: 0; border: 0; border-radius: 14px; color: var(--orbital-text, #172033); background: var(--orbital-surface, #fff); box-shadow: 0 24px 70px rgb(15 23 42 / 28%); }
  .queue-dialog::backdrop { background: rgb(15 23 42 / 48%); }
  .queue-card { display: grid; gap: 16px; padding: 20px; }
  .queue-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
  .queue-head h2 { margin: 0; font-size: 1.12rem; }
  .queue-head p { margin: 4px 0 0; color: var(--orbital-muted-text, #667085); }
  .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
  label { display: grid; gap: .4rem; font-weight: 650; color: var(--orbital-text, #344054); }
  select { width: 100%; border: 1px solid var(--orbital-border, #cfd8e5); border-radius: .55rem; padding: .75rem; font: inherit; background: var(--orbital-input-bg, #fff); color: var(--orbital-text, #172033); }
  .queue-progress-box { padding: 14px; border: 1px solid var(--orbital-border, #dbe3ee); border-radius: 10px; background: var(--orbital-muted-surface, #f9fafb); }
  .queue-progress-row { display: flex; justify-content: space-between; margin-bottom: 8px; }
  .queue-progress-box progress { width: 100%; height: 12px; }
  .queue-progress-box p { margin: 8px 0 0; color: var(--orbital-muted-text, #667085); font-size: .86rem; }
  .queue-summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
  .queue-summary span { padding: 10px; border: 1px solid var(--orbital-border, #dbe3ee); border-radius: 8px; text-align: center; font-size: .78rem; }
  .queue-summary strong { display: block; font-size: 1.1rem; }
  .queue-actions { display: flex; justify-content: flex-end; gap: 8px; flex-wrap: wrap; }
  @media (max-width: 800px) {
    .page-head { flex-direction: column; }
    .form-grid { grid-template-columns: 1fr; }
  }
  @media (max-width: 560px) { .queue-summary { grid-template-columns: repeat(2, 1fr); } }
`;
