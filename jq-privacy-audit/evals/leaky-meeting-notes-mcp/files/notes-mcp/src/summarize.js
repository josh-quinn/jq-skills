import OpenAI from 'openai';

export async function summarize(transcript) {
  if (!process.env.OPENAI_API_KEY) return 'Summaries are off: set OPENAI_API_KEY.';
  const client = new OpenAI();
  const res = await client.chat.completions.create({
    model: 'gpt-4.1-mini',
    messages: [
      { role: 'system', content: 'Summarise this meeting with decisions and action items.' },
      { role: 'user', content: transcript.text },
    ],
  });
  return res.choices[0].message.content;
}
