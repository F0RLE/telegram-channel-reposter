
// Helper function to remove quotes from strings
export function removeQuotes(str: string): string {
    if (typeof str !== 'string') return str || '';
    let result = str;
    // Replace escaped quotes in the middle
    result = result.replace(/\\'/g, "'");
    result = result.replace(/\\"/g, '"');
    // Remove quotes from start/end (multiple passes for nested quotes)
    while (result.match(/^\\?['"]|\\?['"]$/)) {
        result = result.replace(/^\\?['"]+|\\?['"]+$/g, '');
    }
    return result;
}
