/**
 * All static UI copy for the field app, in one file so it can be reviewed for reading age
 * (target: 9 to 11). Rules: answer first, short sentences, buttons start with a verb.
 * Risk wording is never written here: it comes from the API, word for word. The risk is
 * counted from past years, so this file never says what the weather is going to do.
 */
export const copy = {
  brand: 'GrowÉire',

  steps: [
    {
      short: 'Where',
      title: 'Where is your field?',
      hint: 'Find your town or townland. Then tap your field on the map.',
    },
    {
      short: 'What you grew',
      title: 'What did you grow here?',
      hint: 'Tap the crop you grew last year.',
    },
    {
      short: 'What matters',
      title: 'What matters most to you?',
      hint: 'Pick up to 3 things. The first one you tap counts the most.',
    },
    {
      short: 'Your answer',
      title: 'Your answer',
      hint: 'Your riskiest month, and your rotation next to other options.',
    },
  ],
  stepsGroup: 'Your field',
  stepCounter: (step: number, total: number) => `Step ${step} of ${total}`,
  stepState: { done: 'done', now: 'you are here', next: 'not done yet' },

  back: 'Back',
  next: 'Next',
  backToField: 'Back to my field',
  loading: 'Loading…',
  retry: 'Try again',
  yes: 'Yes',
  no: 'No',
  moreDetail: 'More detail',
  source: 'Source',

  /** Under every recommendation (PRD DD-16). */
  disclaimer: 'This is a guide, not an order. You decide. Check with your advisor.',

  field: {
    none: 'No field chosen yet',
    summary: (name: string | null | undefined, ha: string) => `${name ?? 'Your field'} · ${ha} ha`,
    menuLabel: 'Field menu',
    startNew: 'Start a new field',
    changeAnswers: 'Change my answers',
    home: 'Go to the GrowÉire home page',
    loading: 'Finding your field…',
    findAgain: 'Find my field again',
    outsidePilot: 'Our risk counts are built for Ireland. Here you see weather and soil only.',
  },

  where: {
    searchLabel: 'Town or townland',
    searchPlaceholder: 'For example Bagenalstown',
    searchButton: 'Find',
    searching: 'Searching…',
    noResults: "We couldn't find that place. Tap your field on the map instead.",
    results: 'Places we found',
    tapHint: 'Tap the middle of your field on the map.',
    placed: 'Your field is marked. Tap the map again to move it.',
    sizeQuestion: 'About how big is it?',
    size: (ha: number, acres: number) => `${ha} ha (${acres} acres)`,
    sizeOther: 'Other size',
    sizeOtherLabel: 'Size in hectares',
    sizeRange: 'From 0.1 to 2,000 hectares.',
    satelliteShow: 'Show satellite photo',
    satelliteHide: 'Hide satellite photo',
    usePlace: 'Use the place I searched',
    usePlaceHint: 'This marks a 10 ha field at that place.',
    draw: "Draw my field's edges instead",
    drawHint: 'Tap each corner of your field on the map.',
    drawCorners: (n: number) => (n === 1 ? '1 corner' : `${n} corners`),
    drawArea: (ha: string) => `About ${ha} ha`,
    drawUndo: 'Undo last corner',
    drawStop: 'Stop drawing',
    needPlacement: 'Tap your field on the map first.',
    needCorners: 'Tap at least 3 corners of your field.',
    current: 'This is your field.',
    currentHint: 'To change it, tap the map in a new spot.',
  },

  crops: {
    years: ['Last year', '2 years ago', '3 years ago', '4 years ago'],
    notSure: 'Not sure',
    sameAsLast: 'Same as last year',
    earlier: 'Add earlier years',
    earlierHint: 'Only if you know them. It helps us compare.',
    needLast: 'Tap the crop you grew last year.',
    firstLook: 'A first look at your field',
  },

  priorities: {
    cards: {
      income_stability: 'Steady income',
      simplicity: 'Less work',
      soil_cover: 'Keep soil covered',
      water_use: 'Use less water',
      forage_value: 'Feed for my animals',
      nitrogen_fixing: 'Fix nitrogen',
      pest_break: 'Fewer weeds and pests',
      market_suitability: 'Easy to sell',
    },
    rank: (n: number) => `Number ${n}`,
    full: 'You can pick 3. Tap one again to remove it.',
    questions: 'Three quick questions',
    livestock: 'Do you keep livestock?',
    contract: 'Do you have a contract for a crop?',
    contractWhich: 'For which?',
    exclude: "Is there a crop you won't grow?",
    excludeWhich: 'Which ones?',
  },

  answer: {
    loading: 'Counting the years for your field…',
    months: 'Month by month',
    monthHint: 'Tap a month to see what happened in it.',
    riskiest: 'Riskiest',
    allTypes: 'All weather types this month',
    ofYears: (hit: number, total: number) => `${hit} of ${total} years`,
    recent: (recent: string, long: string, total: number) =>
      `In the last 10 years: ${recent}. Over ${total} years: ${long}.`,
    share: (share: string) => `Share of years counted: ${share}`,
    range: (low: number, high: number, total: number) =>
      `With only ${total} years of records, the true number could be between ${low} and ${high} in 10.`,
    matters: (crop: string, word: string) => `How much this month matters for ${crop}: ${word}.`,
    mattersWords: { little: 'little', some: 'some', lot: 'a lot' },
    localReview: 'Our day-count rules are not checked yet. Ask your advisor if this fits your farm.',
    gaps: "What we don't know yet",
    gapsMore: (n: number) => `and ${n} more`,
    gapsLess: 'Show fewer',
    area: {
      title: (from: number, to: number) => `Your area, ${from} to ${to}`,
      chart: 'How green each summer was',
      lowest: 'Least green summers',
      also: (year: number, month: string) => `${year} was also counted as a dry ${month} here.`,
    },
    soil: {
      title: 'Your soil',
      numbers: 'Soil numbers',
      sources: { pilot_grid: 'Irish soil grid', soilgrids: 'Global soil model' },
      rows: {
        clay: 'Clay (parts in 100)',
        sand: 'Sand (parts in 100)',
        soc: 'Carbon in the soil (g per kg)',
        phh2o: 'Acidity (pH)',
        bdod: 'Soil density (kg per litre)',
        drainage_class: 'Drainage class (1 best to 5 worst)',
        elev_m: 'Height above sea (m)',
        slope_deg: 'Slope (degrees)',
      },
    },
    climate: {
      title: 'Normal weather here',
      period: (period: string) => `Averages for ${period}.`,
      rain: 'Rain (mm)',
      thirst: "The weather's thirst (mm)",
      frost: 'Frost days',
      hot: 'Hot days',
      month: 'Month',
    },
    trends: {
      title: 'How it has changed',
      rain: (mm: string, years: number) => `About ${mm} mm of rain a year per decade, over ${years} years.`,
      tmax: (c: string) => `Daytime highs changed by about ${c} °C per decade.`,
      frost: (days: string) => `Frost days changed by about ${days} a year per decade.`,
      more: 'more',
      less: 'less',
    },
    series: {
      title: 'Crop greenness, month by month',
      text: (from: string, to: string) => `Seen by satellite from ${from} to ${to}. Taller is greener.`,
    },
    sources: 'Where this comes from',
  },

  options: {
    title: 'Your rotation and other options',
    loading: 'Comparing rotations for your field…',
    yours: 'Your rotation',
    startingPoint: 'This is your starting point.',
    year: (n: number) => `Year ${n}`,
    coverAfter: 'then over winter',
    vs: {
      risk: { label: 'Risk', lower: 'lower', same: 'same', higher: 'higher' },
      bare_soil: { label: 'Bare soil', less: 'less', same: 'same', more: 'more' },
      workload: { label: 'Work', less: 'less', same: 'same', more: 'more' },
    },
    rules: {
      ok: 'Meets the crop rules',
      check: 'Check the crop rules',
      unknown: "Two-crop rule not checked: we don't know your tillage area.",
    },
    why: 'Why this option?',
    blocks: {
      why: 'Why',
      evidence: 'Evidence',
      benefits: 'What you gain',
      gaps: "What we don't know yet",
      check: 'What to check on your farm',
    },
    ask: 'Ask your advisor:',
    showAnother: 'Show another option',
    criteria: {
      climate_risk: 'Copes with the weather',
      income_stability: 'Steady income',
      simplicity: 'Less work',
      soil_cover: 'Soil kept covered',
      water_use: 'Uses less water',
      forage_value: 'Feed for animals',
      nitrogen_fixing: 'Fixes nitrogen',
      pest_break: 'Breaks weeds and pests',
      market_suitability: 'Easy to sell',
    } as Record<string, string>,
    criteriaTitle: 'How it does on each point',
    criteriaScale: 'A longer bar is better.',
    rankedBy: (list: string) => `We ranked by: ${list}.`,
    most: 'most',
    metrics: {
      bare: (months: string) => `Bare soil for about ${months} months a year.`,
      water: (mm: number) => `The crops use about ${mm} mm of water a year.`,
      nitrogen: (years: number) =>
        years === 1 ? '1 year in 4 fixes nitrogen.' : `${years} years in 4 fix nitrogen.`,
    },
  },

  share: {
    print: 'Print',
    send: 'Send',
    warning: "This link shows your field's location to whoever you send it to.",
    whatsapp: 'Send by WhatsApp',
    sms: 'Send by text',
    email: 'Send by email',
    copy: 'Copy the link',
    copied: 'Link copied.',
    text: 'My field answer from GrowÉire:',
    subject: 'My field answer from GrowÉire',
  },

  print: {
    title: 'Your field answer',
    date: (date: string) => `Printed on ${date}`,
    monthTable: { month: 'Month', word: 'Weather (risk)', how: 'How often' },
    link: 'See it again at',
    back: 'Back to my answer',
  },

  more: {
    group: 'More',
    menu: 'More',
    maps: { label: 'More maps', hint: 'Satellite pictures and the risk map for any month.' },
    words: { label: 'What the words mean', hint: 'Plain meanings for the words we use.' },
    sources: { label: 'Data and sources', hint: 'Where the numbers come from, and what we do not know yet.' },
  },
  whatDoesThisMean: 'What does this mean?',
  words: 'Words',

  maps: {
    layers: 'What to show',
    month: 'Month',
    type: 'Weather type',
    allTypes: 'All',
    legend: (month: string, type: string) => `Risk in ${month}, ${type}`,
    legendAll: 'all weather types',
    legendCuts: {
      low: 'fewer than 1 year in 10',
      medium: '1 year in 10 to 1 in 4',
      high: 'more than 1 year in 4',
    },
    dryNote: 'Dry months are rare in most of Ireland, so most of this map is low.',
    day: 'Day',
    noPicture: 'No picture for this day? There were clouds, or no satellite pass. Try another day.',
    cellHint: 'Tap a square on the map to see its count.',
  },

  sourcesPage: {
    howTitle: 'How the risk is counted',
    how: [
      'We use 25 years of NASA weather for your area.',
      'A soil water model from Met Éireann and Teagasc turns that weather into dry days and wet days.',
      'A month counts as bad when it had too many dry, wet, hot or frosty days.',
      'We count how many of the 25 years had a bad month. That count is the risk.',
      'The day rules are our own. An advisor has not checked them yet.',
      'The weather is for an area about 50 km wide. The soil is for your field. We do not forecast.',
    ],
    dataTitle: 'Where the data comes from',
    dataHint: 'Find a field first to see every source used for it.',
  },

  panel: {
    show: 'Show the steps',
    hide: 'Hide the steps',
  },

  map: {
    label: 'Map of your area',
    loading: 'Loading the map…',
    failed: 'The map did not load. Check your connection, then load the page again.',
    bigger: 'Bigger map',
    smaller: 'Smaller map',
    marker: 'Your field',
  },

  risk: {
    levels: { low: 'Low', medium: 'Some', high: 'High' },
    types: { drought: 'Dry', waterlogging: 'Wet', heat: 'Heat', frost: 'Frost' },
  },

  errors: {
    place_search_busy: {
      message: 'Search is busy.',
      next: 'Tap your field on the map instead.',
    },
    field_not_found: {
      message: 'This link is out of date.',
      next: 'Find your field again.',
    },
    invalid: {
      message: 'We could not use that.',
      next: 'Go back one step and try again.',
    },
    too_large: {
      message: 'That shape is too big for us to read.',
      next: 'Tap the middle of your field and pick a size instead.',
    },
    data_unavailable: {
      message: 'One of our data sources is not answering.',
      next: 'Wait a minute, then try again.',
    },
    offline: {
      message: 'You seem to be offline.',
      next: 'Check your signal, then try again.',
    },
    unknown: {
      message: 'Something went wrong on our side.',
      next: 'Try again. Your answers are kept.',
    },
  },
} as const

export type ErrorKey = keyof typeof copy.errors
