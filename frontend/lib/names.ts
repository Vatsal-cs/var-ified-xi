/** For text shown in capitals. CSS uppercase turns "ß" into "SS", so Groß
 *  reads GROSS; the capital ẞ keeps the name as it is spelt (GROẞ). */
export const caps = (text: string) => text.replace(/ß/g, "ẞ");
