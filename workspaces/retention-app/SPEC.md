# Retention App — Idea Parking Lot

> Native iOS app that helps professionals retain insights from books, articles, podcasts, and talks using spaced repetition. Not flashcards for exams — "morning inspiration" micro-review sessions.

**Status:** Parked. Build after SubTracker is live and generating revenue.

---

## One-Line Pitch

"Remember everything you read — 2 minutes a day."

---

## The Problem

You read a great book 6 months ago and can't recall a single actionable insight. Knowledge decays exponentially without review (Ebbinghaus forgetting curve). SR produces 85% better retention after 30 days vs. passive re-reading. But no consumer app makes this feel effortless for non-students.

---

## Target User

- Professionals who read 12-30 nonfiction books/year
- High income, high education, 25-45
- Currently using: Kindle highlights (never reviewed), Notion/Obsidian (over-engineered), or nothing
- Communities: r/books (16M), r/productivity (2M), BookTube/BookTok (nonfiction subset)

---

## Competitive Landscape

| Competitor | Price | Weakness to Exploit |
|------------|-------|---------------------|
| **Readwise** | $8.99/mo | Complex, web-first heritage, expensive for casual users, focused on capture not reflection |
| **Anki** | $25 iOS | Hideous UX, manual card creation, designed for medical students not professionals |
| **Obsidian + SR plugin** | Free + setup | Enormous friction, desktop-first, breaks frequently, requires markdown knowledge |
| **Headway/Blinkist** | Subscription | Pre-written summaries, not YOUR insights from YOUR reading |
| **Bloomind** | Free | 1 App Store rating; virtually unknown; early/unpolished |
| **Recall AI** | Free? | Browser-focused, auto-summarization, unclear traction |

### Readwise's Moat (respect it)

- 4M users, ~$3.5-14M ARR, bootstrapped, profitable
- 8 years of integrations (Kindle, Apple Books, Snipd, 20+ sources)
- Native iOS app already exists
- "Mastery" feature already does SR for highlights
- 90%+ retention rate
- Strong brand in this exact niche

---

## Differentiation Angle (What Readwise Doesn't Do)

1. **AI-generated reflection prompts** — User enters a book title → app generates thoughtful questions ("What did Kahneman mean by the difference between experiencing self and remembering self? How has this shown up in your life?"). Removes the #1 friction point: writing your own cards.
2. **2-minute micro-sessions** — 5 cards max, never more. Positioned as "morning inspiration" not "study." No guilt, no backlog anxiety.
3. **One-time purchase ($7.99)** — Directly undercuts Readwise's $8.99/mo for users who don't need the full capture pipeline.
4. **Zero setup cold start** — "Name 3 books you read this year" → instant review content on day 1, before user highlights anything.
5. **Native iOS with widget** — Widget shows one random insight each day. Passive retention without opening the app.

---

## Structural Risks (Why This Is Hard)

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Daily habit formation required | High | Micro-sessions (2 min), no guilt mechanics, adaptive scheduling |
| Cold start (empty app on day 1) | High | AI prompt generation from book titles; no content input required upfront |
| "Guilt app" phenomenon | High | Skip-friendly design, no backlog, "morning inspiration" framing |
| Readwise is the direct incumbent | High | Different positioning (reflection vs. capture), one-time price, simpler UX |
| Benefits invisible for 1-2 months | Medium | Gamification (streak, "books retained" count), early testimonials |
| AI summarization eroding value | Medium | Position on retention (review loop), not recall (one-shot lookup) |
| Market ceiling (~$5-10K/mo indie scale) | Low | Acceptable as second app alongside SubTracker |
| 6-7% average 30-day app retention | High | Duolingo-style streak mechanics; notifications that feel like value, not nagging |

---

## Technical Architecture (Sketch)

| Layer | Choice |
|-------|--------|
| UI | SwiftUI, iOS 17+ |
| Data | SwiftData + CloudKit |
| AI prompts | On-device (Core ML) or OpenAI API for generation |
| SR algorithm | FSRS (Free Spaced Repetition Scheduler — open source, modern) |
| Widget | WidgetKit — daily insight card |
| Backend | Minimal — only if using cloud AI for prompt generation |

### Data Model (Draft)

```swift
@Model class Book {
    var id: UUID
    var title: String
    var author: String?
    var dateRead: Date?
    var coverColor: String?     // generated from title if no image
    var insights: [Insight]
}

@Model class Insight {
    var id: UUID
    var book: Book
    var content: String         // the highlight or takeaway
    var promptQuestion: String? // AI-generated reflection question
    var source: Int16           // enum: manual, kindle, ai_generated
    var nextReviewDate: Date
    var interval: Double        // days until next review (FSRS)
    var easeFactor: Double      // FSRS difficulty rating
    var reviewCount: Int16
    var lastReviewedAt: Date?
}

@Model class ReviewSession {
    var id: UUID
    var date: Date
    var insightsReviewed: Int16
    var durationSeconds: Int16
    var streakDay: Int16
}
```

---

## Build Estimate

- **MVP (2 weeks):** Manual insight entry, book catalog, FSRS review engine, daily session UI, streak tracking, widget
- **V1.1 (week 3-4):** AI prompt generation (OpenAI API), Kindle highlight import, share sheet intake
- **V1.2:** Social features (share an insight card), Shortcuts integration, Apple Watch

---

## Go-to-Market

| Channel | Approach |
|---------|----------|
| Reddit | r/books, r/productivity — "I built an app to remember what I read" |
| BookTube/BookTok | "What I retained from 20 books this year" content |
| Product Hunt | Natural fit for this audience |
| Newsletters | Pitch to productivity/reading newsletters (Ali Abdaal's audience, Tiago Forte's audience) |
| Readwise refugees | Price-sensitive Readwise users who only want review, not capture |

---

## Decision Criteria (When to Build)

Build this when:
- [ ] SubTracker is live on App Store and generating consistent downloads
- [ ] You have bandwidth for a second app (not splitting focus during SubTracker launch)
- [ ] You've validated the AI prompt generation quality (can GPT-4 generate genuinely thoughtful reflection questions from just a book title?)
- [ ] You've personally used a manual version for 2+ weeks and found the habit sticky

---

## Key Research References

- Andy Matuschak's mnemonic medium notes: notes.andymatuschak.org
- Michael Nielsen's "Augmenting Long-term Memory": augmentingcognition.com/ltm.html
- FSRS algorithm: github.com/open-spaced-repetition/fsrs4anki
- Readwise's bootstrapping philosophy: blog.readwise.io/why-were-bootstrapping-readwise/
- Heyday post-mortem (raised $6.5M, dead by 2025): proof that passive memory alone doesn't monetize
