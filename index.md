---
layout: home
---

# English OpenList Blog

**Daily updates • Interactive statistics • Transparent automation**

Welcome to the official blog of the English OpenList project — the largest open-source, Scrabble-compatible English word list.

Every day we discover new words, validate candidates, update our dataset on Hugging Face, and publish a detailed report right here.

## Latest Posts

{% for post in site.posts limit:5 %}
- [{{ post.title }}]({{ post.url | relative_url }}) — {{ post.date | date: "%B %d, %Y" }}
{% endfor %}

## Quick Links

- [Hugging Face Dataset](https://huggingface.co/datasets/ryanjosephkamp/english-openlist)
- [GitHub Repository](https://github.com/ryanjosephkamp/english-openlist)
- [Daily Updates](https://github.com/ryanjosephkamp/english-openlist/actions)

*New daily posts begin automatically starting tomorrow.*