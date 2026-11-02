import { describe, expect, it } from 'vitest';
import { buildRuns, parsePost } from './runs.ts';

const post = (date: string, body: string) =>
  parsePost(
    `${date}-daily-update.md`,
    `---\ntitle: "x"\n---\n\n**Generated automatically at ${date} 05:48:56 UTC**\n\n## Today's Results\n\n${body}`,
  );

const figures = (added: number, promoted: number, total: string, invalid: string) =>
  [
    `- **Total words added today:** ${added}`,
    '- **New words discovered today:** 0',
    `- **Words promoted from invalid list:** ${promoted}`,
    `- **Total valid words now:** **${total}**`,
    `- **Total invalid entries tracked:** ${invalid}`,
  ].join('\n');

describe('parsePost', () => {
  it('reads the figures, the promoted words, and the time', () => {
    const p = post('2026-08-27', `${figures(2, 2, '345,128', '9,308,871')}\n\n### Words Promoted Today\n\n\`\`\`text\nsincerity\nseminarist\n\`\`\``);
    expect(p).toMatchObject({
      date: '2026-08-27',
      at: '2026-08-27T05:48:56Z',
      added: 2,
      promoted: 2,
      total: 345_128,
      invalid: 9_308_871,
      promotedWords: ['sincerity', 'seminarist'],
    });
  });

  it('reads "not recorded" as no figure', () => {
    const p = post('2026-05-14', figures(0, 0, 'not recorded', 'not recorded').replace(/\*\* 0$/gm, '** not recorded'));
    expect(p.added).toBeNull();
    expect(p.total).toBeNull();
  });
});

describe('buildRuns', () => {
  const growth = {
    points: [
      { date: '2026-08-26', total: 100 },
      { date: '2026-08-27', total: 102 },
      { date: '2026-09-19', total: 102 },
    ],
  };

  it('takes the words from the list and the figures from the post', () => {
    const p = post('2026-08-27', `${figures(2, 2, '102', '50')}\n\n### Words Promoted Today\n\n\`\`\`text\nsincerity\naflatoxin\n\`\`\``);
    const dated = new Map([['2026-08-27', [{ word: 'sincerity', decided: 0 }, { word: 'seminarist', decided: 0 }]]]);
    const [run] = buildRuns([p], dated, growth);
    expect(run!.words).toEqual([
      { word: 'sincerity', decided: 0, how: 'promoted' },
      { word: 'seminarist', decided: 0, how: 'dated' },
    ]);
    // named by the post, not dated that day by the list
    expect(run!.missing).toEqual(['aflatoxin']);
    expect(run).toMatchObject({ total: 102, before: 100, failed: false });
    expect(run!.recorded).toEqual({ added: 2, promoted: 2, discovered: 0, invalid: 50 });
  });

  it('marks a run that recorded the list as 0 words as failed', () => {
    const p = post('2026-09-19', figures(0, 0, '0', '0'));
    const [run] = buildRuns([p], new Map(), growth);
    expect(run).toMatchObject({ failed: true, recorded: null, total: null, before: null });
  });
});
