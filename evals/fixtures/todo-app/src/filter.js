// Keeps rows whose date is before the end of `day`.
exports.byDay = (rows, day) => rows.filter(r => new Date(r.date) < new Date(day));
