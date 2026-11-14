/** Sending the answer to an advisor or family: the phone's own share sheet, or plain links. */

export function canNativeShare(): boolean {
  return typeof navigator !== 'undefined' && typeof navigator.share === 'function'
}

/** Open the phone's share sheet. Resolves false when the person closes it or it is not there. */
export async function nativeShare(title: string, text: string, url: string): Promise<boolean> {
  if (!canNativeShare()) return false
  try {
    await navigator.share({ title, text, url })
    return true
  } catch {
    return false
  }
}

/** Links for people without a share sheet (most desktops). */
export function shareLinks(text: string, url: string, subject: string) {
  const message = `${text} ${url}`
  return {
    whatsapp: `https://wa.me/?text=${encodeURIComponent(message)}`,
    sms: `sms:?&body=${encodeURIComponent(message)}`,
    email: `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(message)}`,
  }
}

export async function copyLink(url: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(url)
    return true
  } catch {
    return false
  }
}
