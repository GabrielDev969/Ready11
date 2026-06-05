# GSS Monitoring — Design System

Sistema de design para o **GSS Innovations Sports Monitoring** — plataforma de
monitoramento esportivo (futebol) que rastreia prontidão, recuperação, hidratação
e triagem clínica de atletas a partir de check-ins diários.

A identidade é **minimalismo estruturado**: fundo neutro quente, tipografia limpa,
e cor saturada usada *exclusivamente* para dados semânticos calculados pelo motor de
bem-estar (`wellnessEngine`). Construído para **React** (protótipo) e portável para
**Tailwind CSS 3 + Django** (produção).

---

## Índice de arquivos

| Arquivo | Conteúdo |
|---|---|
| `styleguide.html` | **Referência visual viva** — abra primeiro. Cores, tipo, semântica, componentes, ícones, gráficos, forms. |
| `icons.html` | Biblioteca completa de ícones por categoria (nav, saúde, ações). |
| `dataviz.html` | Galeria de gráficos: sparkline, linha dupla, barras, ring meter, heatmap, progresso. |
| `forms.html` | Todos os controles de formulário do wizard de check-in. |
| `tokens.css` | Fonte da verdade: todas as variáveis CSS (cor, tipo, espaço, raio, sombra). |
| `tailwind.config.js` | Todos os tokens mapeados para o tema do Tailwind 3. |
| `gss-components.css` | Classes `.gss-*` em `@layer components` (botão, pill, card, input, tabela…). |
| `DJANGO.md` | Guia passo a passo de instalação e uso no Django. |
| `SKILL.md` | Manifesto para uso como Agent Skill. |

> O **protótipo funcional completo** está na raiz do projeto (`index.html` + `app.jsx`
> + `screens/`): login, 3 dashboards por role, lista/detalhe de atletas e o wizard de
> check-in em 4 passos. O design system documenta os fundamentos usados ali.

---

## Fundamentos visuais

- **Superfícies:** neutros quentes — `#FAFAF7` (fundo), `#FFFFFF` (cards), `#F3F2EE`
  (rebaixado), `#0B0B0D` (inverso). Sem cinzas frios.
- **Cor = significado.** A interface é ~95% neutra. Cor saturada só aparece em status
  clínicos (wellness, hidratação, recuperação, alerta). Nunca decorativa.
- **Tipografia:** IBM Plex Sans (UI) + IBM Plex Mono. Toda **métrica numérica, rótulo
  (eyebrow) e célula de dado é mono e tabular** — é o que dá a vibe técnica/clínica.
- **Forma:** raios discretos (6/10/14px). Cards = borda de 1px + sombra quase
  imperceptível; a hierarquia vem de borda e fundo, não de drop-shadow.
- **Densidade:** alta, orientada a dados. Tabelas de triagem com gradiente sutil de
  fundo na linha (vermelho p/ CRITICAL, âmbar p/ WARNING) puxando da esquerda.
- **Movimento:** discreto. `fade-in-up` na entrada de telas (0.32s, ease
  `cubic-bezier(0.2,0.7,0.2,1)`). Um único `pulse-ring` no ponto de alerta crítico.
  Hover = mudança de fundo para `sunken`; press = `translateY(0.5px)`.
- **Espaço:** escala de 4px (4 · 8 · 12 · 16 · 24 · 32 · 40).

## Cores semânticas (o motor de bem-estar)

| Enum | Visual | Significado |
|---|---|---|
| `EXCELLENT` | verde claro / verde escuro | perfeitas condições de prontidão |
| `GOOD` | azul claro / azul escuro | fadiga adaptativa normal |
| `WARNING` | âmbar claro / âmbar escuro | atenção — moderar carga interna |
| `CRITICAL` | vermelho claro / vermelho escuro | risco de lesão ou overtraining |
| `HYDRATED / ATTENTION / DEHYDRATED` | azul / laranja / vermelho | janela hídrica |
| `GREEN / YELLOW / RED` | semáforo | status de recuperação |

Definidas em `oklch()` para uniformidade perceptual e ajuste fácil de matiz.

---

## Fundamentos de conteúdo

- **Idioma:** português (BR). Rótulos de UI em PT; enums de status mantidos em
  inglês maiúsculo (`CRITICAL`, `DEHYDRATED`) por fidelidade ao contrato de backend.
- **Tom:** clínico, direto, sem firulas. "Triagem prioritária", "Risco iminente de
  lesão", "Reforce a ingestão hídrica". Trata o atleta por nome ("Olá, Henrique").
- **Números primeiro.** Cada métrica vem acompanhada de unidade (`4.2 / 5`, `2.5L`,
  `6/10`) e, quando possível, contexto (meta, média de 14 dias, tendência).
- **Sem emoji** na interface de dados (exceto ✓/⚠ pontuais em dicas do wizard).
- **Eyebrows mono maiúsculas** rotulam todo bloco ("COMISSÃO TÉCNICA · HOJE").

## Iconografia

Ícones desenhados em linha (stroke 1.6px, grid 24×24, estilo Lucide), monocromáticos,
herdando `currentColor` — a cor vem sempre do contexto (texto, status, botão). A
biblioteca completa, organizada por categoria (navegação, métricas & saúde, ações &
estados), está em **`icons.html`**. Para produção recomenda-se **Lucide**
(`https://unpkg.com/lucide` ou pacote npm) — mesmo peso de traço, basta referenciar pelo
nome. Sem emoji como ícone; sem PNGs. A "escala de cor de urina" (1–8, amarelo→marrom) é
o único uso de cor ilustrativa, e é funcional (escala de Armstrong), não decorativa.

## Gráficos & visualização de dados

Gráficos são SVG leves, sem dependência de biblioteca: sparkline, linha dupla
comparativa, barras (PSE/hidratação), ring meter (scores), barra de distribuição
empilhada, barra de progresso e heatmap de incidência de sintomas. Linhas finas
(1.5–2px), sem grids pesados, números tabulares, e a **cor do dado segue o status
semântico** — nunca uma paleta arbitrária. Galéria completa em **`dataviz.html`**.

---

## Como iterar

Edite **somente `tokens.css`** para mudar a marca — todo o resto deriva dele.
Para mudar uma cor semântica, ajuste os 3 valores `oklch(claridade chroma matiz)`.

> **Compartilhamento:** defina o tipo de arquivo como *Design System* no menu Share
> para que o restante da sua organização consiga visualizar.
