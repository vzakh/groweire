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
      hint: 'Tap the crop you grew last year. Add earlier years if you know them.',
    },
    {
      short: 'What matters',
      title: 'What matters most to you?',
      hint: 'Pick up to 3 things. The first one you tap counts the most.',
    },
    {
      short: 'Your answer',
      title: 'Your answer',
      hint: 'See your riskiest month. Compare your rotation with two other options.',
    },
  ],
  stepsGroup: 'Your field',
  stepCounter: (step: number, total: number) => `Step ${step} of ${total}`,
  stepState: { done: 'done', now: 'you are here', next: 'not done yet' },
  notBuiltYet: 'We are still building this part.',

  back: 'Back',
  next: 'Next',
  backToField: 'Back to my field',

  field: {
    none: 'No field chosen yet',
    menuLabel: 'Field menu',
    startNew: 'Start a new field',
    changeAnswers: 'Change my answers',
    home: 'Go to the GrowÉire home page',
  },

  more: {
    group: 'More',
    menu: 'More',
    maps: { label: 'More maps', hint: 'See the satellite pictures and the risk map for any month.' },
    words: { label: 'What the words mean', hint: 'Plain meanings for the words we use.' },
    sources: { label: 'Data and sources', hint: 'Where the numbers come from, and what we do not know yet.' },
  },
  whatDoesThisMean: 'What does this mean?',
  words: 'Words',

  panel: {
    show: 'Show the steps',
    hide: 'Hide the steps',
  },

  map: {
    label: 'Map of your area',
    loading: 'Loading the map…',
    failed: 'The map did not load. Check your connection, then load the page again.',
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
