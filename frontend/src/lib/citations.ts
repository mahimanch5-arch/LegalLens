/** Turns `[3]` markers into `[3](#cite-3)` links, which the Markdown renderer swaps for chips. */
export function linkCitations(md: string, streaming = false): string {
  // While streaming, hide a half-received marker such as "[1" at the very end.
  const text = streaming ? md.replace(/\[\d*$/, '') : md;
  return text.replace(/\[(\d+)\](?!\()/g, '[$1](#cite-$1)');
}
