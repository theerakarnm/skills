// Thai word segmentation with Intl.Segmenter (ICU), used by captions.py for auto-chunking.
// stdin: JSON list of strings. stdout: JSON list of lists of words.
// Note: ICU mis-splits loanwords and brands (แชท -> แช|ท, มันม่วง -> มัน|ม่วง);
// captions.py re-joins them with the keep-together list.
const chunks = [];
process.stdin.on("data", (d) => chunks.push(d));
process.stdin.on("end", () => {
  const items = JSON.parse(Buffer.concat(chunks).toString("utf8"));
  const seg = new Intl.Segmenter("th", { granularity: "word" });
  const out = items.map((s) => [...seg.segment(s)].map((x) => x.segment));
  process.stdout.write(JSON.stringify(out));
});
