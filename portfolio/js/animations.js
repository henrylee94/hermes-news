/**
 * animations.js — narrative GSAP choreography
 * Requires: gsap.min.js, ScrollTrigger.min.js (loaded before this script, deferred).
 * One-shot hero + reveal animations, plus scrubbed diagram storytelling per case study.
 * Reduced-motion aware: DOM default state is already the final visible state, so on
 * prefers-reduced-motion (or missing GSAP/ScrollTrigger) we simply do nothing.
 */
(function () {
  if (!window.gsap || !window.ScrollTrigger) return; // CDN failure: static page stays fully visible

  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduced) return; // final states are the default DOM — nothing to animate

  gsap.registerPlugin(ScrollTrigger);

  // ---------------------------------------------------------------------------
  // 1. Hero: staggered rise, completes ~1s
  // ---------------------------------------------------------------------------
  gsap.timeline({ defaults: { ease: 'power3.out' } })
    .from('.hero-line', { y: 40, opacity: 0, duration: 0.6, stagger: 0.08 })
    .from(['.hero-role', '.hero-positioning', '.hero-sub'], { y: 24, opacity: 0, duration: 0.5, stagger: 0.08 }, '-=0.3')
    .from(['.hero-badge', '.hero-ctas'], { opacity: 0, duration: 0.4 }, '-=0.2');

  // ---------------------------------------------------------------------------
  // 2. Uniform section reveals (fire once on entry)
  // ---------------------------------------------------------------------------
  gsap.utils.toArray('.section-heading, .case-beats > *, .principle, .demo-row, .xp-item, .tier').forEach((el) => {
    gsap.from(el, {
      y: 24,
      opacity: 0,
      duration: 0.6,
      ease: 'power2.out',
      scrollTrigger: { trigger: el, start: 'top 85%', once: true },
    });
  });

  // ---------------------------------------------------------------------------
  // 3. Diagram storytelling (scrubbed to scroll position)
  // ---------------------------------------------------------------------------
  const scrub = (trigger) => ({ trigger, start: 'top 75%', end: 'bottom 45%', scrub: 0.5 });

  // Case 1: dispatch — dots flow → pod-b fails (red) → heal arc draws (green)
  const c1 = document.querySelector('[data-diagram="dispatch"]');
  if (c1) {
    const heal = c1.querySelector('#dg1-heal');
    const podfailRect = c1.querySelector('#dg1-podfail rect');
    const tl1 = gsap.timeline({ scrollTrigger: scrub(c1.closest('.case')) });

    tl1.from('#dg1-dots .dg-dot', { scale: 0, transformOrigin: 'center', stagger: 0.2 })
      .to('#dg1-dots .dg-dot', { x: 120, stagger: 0.15 });

    if (podfailRect) {
      tl1.to(podfailRect, { attr: { stroke: '#EF4444' }, duration: 0.3 });
    }

    if (heal) {
      const len = heal.getTotalLength();
      gsap.set(heal, { strokeDasharray: len, strokeDashoffset: len });
      tl1.to(heal, { strokeDashoffset: 0, duration: 0.6 }, '+=0.1');
    }

    if (podfailRect) {
      tl1.to(podfailRect, { attr: { stroke: '#22C55E' }, duration: 0.3 });
    }
  }

  // Case 2: migration — old fades, new rises, dots keep moving
  const c2 = document.querySelector('[data-diagram="migration"]');
  if (c2) {
    gsap.timeline({ scrollTrigger: scrub(c2.closest('.case')) })
      .to('#dg2-old', { opacity: 0.25 })
      .from('#dg2-new', { opacity: 0, y: 10 }, '<')
      .to('#dg2-dots circle', { x: 30, stagger: 0.1 }, '<');
  }

  // ---------------------------------------------------------------------------
  // 4. Demo card previews — infinite loops, playing only while in viewport.
  //    SVGs are authored in their final visible state (reduced-motion fallback),
  //    so each timeline hides parts via gsap.set before looping.
  // ---------------------------------------------------------------------------

  // Play/pause an infinite timeline based on viewport visibility (saves CPU)
  const loopInView = (trigger, tl) => {
    new IntersectionObserver((entries) => {
      entries.forEach((e) => (e.isIntersecting ? tl.play() : tl.pause()));
    }).observe(trigger);

    // Easter egg: the scene runs "hotter" while hovered
    const media = trigger.closest('.demo-media');
    if (media) {
      media.addEventListener('mouseenter', () => tl.timeScale(1.5));
      media.addEventListener('mouseleave', () => tl.timeScale(1));
    }
  };

  // D1: continuous throughput — three staggered waves stream Temporal → Pulsar → workers
  const dp1 = document.querySelector('[data-demo-anim="pipeline"]');
  if (dp1) {
    const pulsar = dp1.querySelector('#dp1-pulsar rect');
    const tl = gsap.timeline({ repeat: -1, paused: true, defaults: { ease: 'none' } });
    const WAVE = 0.9; // gap between waves keeps dots on the wires almost constantly

    [0, 1, 2].forEach((i) => {
      const din = dp1.querySelector(`#dp1-w${i} circle`);
      const fans = dp1.querySelectorAll(`#dp1-f${i} circle`);
      const at = i * WAVE;

      tl.fromTo(din, { attr: { cx: 124 }, autoAlpha: 0 }, { autoAlpha: 1, duration: 0.15 }, at)
        .to(din, { attr: { cx: 188 }, duration: 0.5 }, at)
        .to(din, { autoAlpha: 0, duration: 0.1 }, at + 0.5)
        .to(pulsar, { scale: 1.06, transformOrigin: 'center', duration: 0.15, ease: 'power1.out' }, at + 0.5)
        .to(pulsar, { scale: 1, duration: 0.25, ease: 'power1.in' }, at + 0.65)
        .fromTo(fans,
          { attr: { cx: 276, cy: 151 }, autoAlpha: 0 },
          { autoAlpha: 1, duration: 0.12, stagger: 0.05 }, at + 0.55)
        .to(fans, { attr: { cx: 366, cy: (j) => [52, 151, 250][j] }, duration: 0.6, stagger: 0.05 }, at + 0.6)
        .to(fans, { autoAlpha: 0, duration: 0.12 }, at + 1.2);
    });

    loopInView(dp1, tl);
  }

  // D2: chat playback — command lands, typing resolves into bot replies
  const dp2 = document.querySelector('[data-demo-anim="chat"]');
  if (dp2) {
    const user = dp2.querySelector('#dp2-user');
    const typing = dp2.querySelector('#dp2-typing');
    const tdots = dp2.querySelectorAll('.dp-tdot');
    const bot = dp2.querySelector('#dp2-bot');
    const bot2 = dp2.querySelector('#dp2-bot2');
    const user2 = dp2.querySelector('#dp2-user2');
    const tl = gsap.timeline({ repeat: -1, paused: true, defaults: { ease: 'power2.out' } });

    tl.set([user, typing, bot, bot2, user2], { autoAlpha: 0 })
      .fromTo(user, { y: 10, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 0.4 }, '+=0.3')
      .to(typing, { autoAlpha: 1, duration: 0.25 }, '+=0.4')
      .to(tdots, { y: -4, duration: 0.25, stagger: 0.1, repeat: 3, yoyo: true, ease: 'power1.inOut' })
      .to(typing, { autoAlpha: 0, duration: 0.15 })
      .fromTo(bot, { y: 8, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 0.4 }, '-=0.05')
      .fromTo(bot2, { y: 8, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 0.4 }, '+=0.35')
      .fromTo(user2, { y: 10, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 0.4 }, '+=0.6')
      .to({}, { duration: 1.6 }) // hold the finished exchange
      .to([user, bot, bot2, user2], { autoAlpha: 0, duration: 0.4 });

    loopInView(dp2, tl);
  }

  // D3: terminal run — command blinks, CI-style lines print, pipeline goes green
  const dp3 = document.querySelector('[data-demo-anim="workflow"]');
  if (dp3) {
    const cmd = dp3.querySelector('#dp3-cmd');
    const cursor = dp3.querySelector('#dp3-cursor');
    const lines = ['#dp3-l1', '#dp3-l2', '#dp3-l3', '#dp3-l4', '#dp3-l5'].map((s) => dp3.querySelector(s));
    const done = dp3.querySelector('#dp3-done');
    const tl = gsap.timeline({ repeat: -1, paused: true, defaults: { ease: 'power1.out' } });

    tl.set([cmd, ...lines, done], { autoAlpha: 0 })
      .set(cursor, { autoAlpha: 1 })
      .to(cmd, { autoAlpha: 1, duration: 0.2 }, 0.3)
      // cursor blinks while the "command" runs
      .to(cursor, { autoAlpha: 0, duration: 0.01, repeat: 5, yoyo: true, repeatDelay: 0.3 }, 0.4);

    lines.forEach((line, i) => {
      tl.fromTo(line, { autoAlpha: 0, x: -6 }, { autoAlpha: 1, x: 0, duration: 0.18 }, 1.2 + i * 0.5);
    });

    tl.fromTo(done, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.25 }, '+=0.3')
      .to({}, { duration: 1.8 }) // hold the green build
      .to([cmd, ...lines, done, cursor], { autoAlpha: 0, duration: 0.4 });

    loopInView(dp3, tl);
  }

  // Case 3: trading — dots converge into gateway, shield pops
  const c3 = document.querySelector('[data-diagram="trading"]');
  if (c3) {
    gsap.timeline({ scrollTrigger: scrub(c3.closest('.case')) })
      // Converge each dot onto the gateway node's top edge (node spans x 100-300, top y ~110)
      .to('#dg3-dots circle', { x: (i) => [70, 0, -70][i], y: 52, stagger: 0.12 })
      .from('#dg3-shield', { scale: 0, transformOrigin: 'center' });
  }
}());
