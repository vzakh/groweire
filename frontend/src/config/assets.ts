/**
 * Visual assets in public/img/.
 * Licence: the hero photo's credit and licence are still to be confirmed before public use
 * (see README).
 *
 * hero.jpg is 2048×1534, the same aspect ratio as the 1800×1348 overlay coordinate space.
 */
export const HERO_IMAGE = '/img/hero.jpg'
export const HERO_IMAGE_ALT =
  'Irish farmland from above in low evening sun: a ploughed field, young cereal crops and hedgerows'

/**
 * Section 4 ("How It Works") screenshot of the real GrowÉire interface.
 * null → a neutral placeholder screen is shown. When the interface exists, put the image in
 * public/img/ and set e.g. '/img/app-screenshot.png' (16:10 works best).
 */
export const HOW_IT_WORKS_SCREENSHOT: string | null = null
export const HOW_IT_WORKS_SCREENSHOT_ALT = 'The GrowÉire field workspace'

/**
 * Signed-in user shown in the header's right corner. There is no login yet, so this is a
 * placeholder profile. `avatar`: an image in public/img/ (e.g. '/img/avatar.jpg'), or null to
 * show the user's initials instead.
 */
export const CURRENT_USER: { nickname: string; avatar: string | null } = {
  nickname: 'Demo farmer',
  avatar: null,
}
