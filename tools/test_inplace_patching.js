// Verification script for Comic Reader In-place Patching & Geometry Persistence
const assert = require('assert');

// 1. Mock Geometry & Classification functions exactly as in src/index.js
const STAGE_WIDTH = 972;
const PORTRAIT_SINGLE_WIDTH = 728;
const WATERFALL_CONTENT_WIDTH = 950;
const DUAL_COLUMN_WIDTH = 474;

const _globalImageSizeCache = new Map();

function classifyPageGeometry(imgW, imgH) {
  const validW = (typeof imgW === 'number' && imgW > 0) ? imgW : 474;
  const validH = (typeof imgH === 'number' && imgH > 0) ? imgH : 632;
  const ratio = validW / validH;
  const isWide = ratio > 1.05;

  let aspectType = 'portrait';
  if (ratio >= 2.0) {
    aspectType = 'ultrawide';
  } else if (ratio > 1.05) {
    aspectType = 'wide';
  } else if (ratio >= 0.90) {
    aspectType = 'square';
  } else if (ratio <= 0.45) {
    aspectType = 'strip';
  } else {
    aspectType = 'portrait';
  }

  const wfWidth = isWide ? WATERFALL_CONTENT_WIDTH : DUAL_COLUMN_WIDTH;
  const cardHeight = Math.max(80, Math.round(wfWidth * (validH / validW)));
  const singleBaseW = isWide ? STAGE_WIDTH : PORTRAIT_SINGLE_WIDTH;
  const singleBaseH = Math.max(80, Math.round(singleBaseW * (validH / validW)));

  return {
    imgW: validW,
    imgH: validH,
    ratio: ratio,
    isWide: isWide,
    aspectType: aspectType,
    cardWidth: wfWidth,
    cardHeight: cardHeight,
    singleBaseWidth: singleBaseW,
    singleBaseHeight: singleBaseH
  };
}

function applyPageGeometry(pageObj, rawW, rawH, markVerified) {
  const geom = classifyPageGeometry(rawW, rawH);
  pageObj.imgW = geom.imgW;
  pageObj.imgH = geom.imgH;
  pageObj.ratio = geom.ratio;
  pageObj.isWide = geom.isWide;
  pageObj.aspectType = geom.aspectType;
  pageObj.cardWidth = geom.cardWidth;
  pageObj.cardHeight = geom.cardHeight;
  pageObj.singleBaseWidth = geom.singleBaseWidth;
  pageObj.singleBaseHeight = geom.singleBaseHeight;
  if (markVerified) {
    pageObj.geometryVerified = true;
  }
  return geom;
}

// 2. Mock state machine
class ComicReaderMock {
  constructor() {
    this.bookshelf = [];
    this.currentBookIndex = 0;
    this.currentPageId = 1;
    this.viewMode = 'waterfall';
    this.layoutVersion = 0;
    this.hasPendingWebp = false;
  }

  get currentBook() {
    return this.bookshelf[this.currentBookIndex] || null;
  }

  mergeBookshelfInPlace(scannedBooks) {
    if (!Array.isArray(this.bookshelf)) {
      this.bookshelf = scannedBooks;
      return;
    }
    if (!Array.isArray(scannedBooks) || scannedBooks.length === 0) return;

    const scannedMap = new Map();
    for (const b of scannedBooks) {
      if (b && b.id) {
        scannedMap.set(b.id, b);
      }
    }

    // 1. 就地增量修补已有书籍状态与页面，保留现有书籍和页面对象引用
    for (const existingBook of this.bookshelf) {
      const newBook = scannedMap.get(existingBook.id);
      if (!newBook) continue;

      existingBook.title = newBook.title;
      existingBook.subtitle = newBook.subtitle;
      existingBook.totalPages = newBook.totalPages;
      existingBook.readyPages = newBook.readyPages;
      existingBook.webpPendingCount = newBook.webpPendingCount;
      existingBook.webpPercent = newBook.webpPercent;
      existingBook.webpDone = newBook.webpDone;
      existingBook.optimizedCount = newBook.optimizedCount;
      existingBook.isFullyOptimized = newBook.isFullyOptimized;
      if (!existingBook.cover && newBook.cover) {
        existingBook.cover = newBook.cover;
      }

      if (Array.isArray(existingBook.pages) && Array.isArray(newBook.pages)) {
        const existPageMap = new Map();
        for (const p of existingBook.pages) {
          if (p && p.fileName) {
            existPageMap.set(p.fileName, p);
          }
        }

        let newPagesAdded = false;
        for (const newP of newBook.pages) {
          const existP = existPageMap.get(newP.fileName);
          if (existP) {
            // 关键属性就地更新，绝对锁死已测定的真实几何！
            if (!existP.hasThumb && newP.hasThumb) {
              existP.hasThumb = true;
              existP.thumbSrc = newP.thumbSrc;
              existP.thumbName = newP.thumbName;
            }
            if (!existP.hasHigh && newP.hasHigh) {
              existP.hasHigh = true;
              existP.highSrc = newP.highSrc;
              existP.highName = newP.highName;
            }
            // 如果此前未验证，而新扫描获得了已验证几何，才补丁
            if (!existP.geometryVerified && newP.geometryVerified) {
              applyPageGeometry(existP, newP.imgW, newP.imgH, true);
            }
          } else {
            // 新增转码完成的页面，赋予递增ID并追加
            newP.id = existingBook.pages.length + 1;
            existingBook.pages.push(newP);
            newPagesAdded = true;
          }
        }

        // 仅当当前正在阅读的书籍真正新增了页面，才通知布局重排
        if (newPagesAdded && this.currentBook && this.currentBook.id === existingBook.id) {
          this.layoutVersion++;
        }
      }
    }

    // 2. 追加新扫描到的书籍
    const existingIds = new Set(this.bookshelf.map(b => b.id));
    for (const newBook of scannedBooks) {
      if (!existingIds.has(newBook.id)) {
        this.bookshelf.push(newBook);
      }
    }

    // 3. 移除已被用户在电脑外部删除的书籍
    for (let i = this.bookshelf.length - 1; i >= 0; i--) {
      if (!scannedMap.has(this.bookshelf[i].id)) {
        this.bookshelf.splice(i, 1);
      }
    }

    if (this.currentBookIndex >= this.bookshelf.length) {
      this.currentBookIndex = Math.max(0, this.bookshelf.length - 1);
    }
  }

  handleImageLoad(pageObj, e) {
    if (!pageObj || !e || !e.size) return;
    const nw = e.size.naturalWidth;
    const nh = e.size.naturalHeight;
    _globalImageSizeCache.set(pageObj.fileName, { w: nw, h: nh });
    if (pageObj.geometryVerified) return;
    applyPageGeometry(pageObj, nw, nh, true);
  }
}

console.log("=== Testing In-Place Patching & Geometry Persistence ===");

const reader = new ComicReaderMock();

// Step 1: Initial scan with 2 pages (unverified default 474x632)
const book1 = {
  id: 'OnePiece_Vol1',
  title: '海贼王',
  subtitle: '第1卷',
  totalPages: 3,
  readyPages: 2,
  webpPendingCount: 1,
  webpPercent: 66,
  webpDone: false,
  optimizedCount: 0,
  isFullyOptimized: false,
  pages: [
    { id: 1, fileName: '01.jpg', src: 'file:///path/01.jpg', thumbSrc: 'file:///path/01.jpg', hasThumb: false, geometryVerified: false },
    { id: 2, fileName: '02.jpg', src: 'file:///path/02.jpg', thumbSrc: 'file:///path/02.jpg', hasThumb: false, geometryVerified: false }
  ]
};
applyPageGeometry(book1.pages[0], 474, 632, false);
applyPageGeometry(book1.pages[1], 474, 632, false);

reader.bookshelf = [book1];
const initialBookshelfRef = reader.bookshelf;
const initialBookRef = reader.bookshelf[0];
const initialPage1Ref = reader.bookshelf[0].pages[0];
const initialPage2Ref = reader.bookshelf[0].pages[1];

console.log("✓ Step 1: Initial bookshelf loaded. Bookshelf ref:", initialBookshelfRef === reader.bookshelf);

// Step 2: Images load and measure real dimensions (Page 1 is portrait 1000x1500, Page 2 is wide 1920x1080)
reader.handleImageLoad(initialPage1Ref, { size: { naturalWidth: 1000, naturalHeight: 1500 } });
reader.handleImageLoad(initialPage2Ref, { size: { naturalWidth: 1920, naturalHeight: 1080 } });

assert.strictEqual(initialPage1Ref.geometryVerified, true);
assert.strictEqual(initialPage1Ref.isWide, false);
assert.strictEqual(initialPage1Ref.cardHeight, Math.round(474 * (1500 / 1000))); // 711
assert.strictEqual(initialPage1Ref.singleBaseWidth, 728);

assert.strictEqual(initialPage2Ref.geometryVerified, true);
assert.strictEqual(initialPage2Ref.isWide, true);
assert.strictEqual(initialPage2Ref.cardWidth, 950);
assert.strictEqual(initialPage2Ref.singleBaseWidth, 972);

console.log("✓ Step 2: Images verified in memory. Page 1 (portrait): cardHeight =", initialPage1Ref.cardHeight, "singleBaseWidth =", initialPage1Ref.singleBaseWidth);
console.log("✓ Step 2: Page 2 (wide): cardWidth =", initialPage2Ref.cardWidth, "singleBaseWidth =", initialPage2Ref.singleBaseWidth);

// Step 3: Polling scan occurs 2s later while background ffmpeg converts files.
// A new thumbnail was generated for page 1 ('01_thumb.jpg'), and page 3 was newly converted!
const rescannedBook = {
  id: 'OnePiece_Vol1',
  title: '海贼王',
  subtitle: '第1卷',
  totalPages: 3,
  readyPages: 3,
  webpPendingCount: 0,
  webpPercent: 100,
  webpDone: true,
  optimizedCount: 1,
  isFullyOptimized: false,
  pages: [
    // Note: fresh scan without .sizes.json would default to 474x632, but our in-place patch MUST NOT overwrite initialPage1Ref geometry!
    { id: 1, fileName: '01.jpg', src: 'file:///path/01.jpg', thumbSrc: 'file:///path/01_thumb.jpg', hasThumb: true, thumbName: '01_thumb.jpg', geometryVerified: false },
    { id: 2, fileName: '02.jpg', src: 'file:///path/02.jpg', thumbSrc: 'file:///path/02.jpg', hasThumb: false, geometryVerified: false },
    { id: 3, fileName: '03.jpg', src: 'file:///path/03.jpg', thumbSrc: 'file:///path/03.jpg', hasThumb: false, geometryVerified: false }
  ]
};
applyPageGeometry(rescannedBook.pages[0], 474, 632, false);
applyPageGeometry(rescannedBook.pages[1], 474, 632, false);
applyPageGeometry(rescannedBook.pages[2], 474, 632, false);

reader.mergeBookshelfInPlace([rescannedBook]);

// Step 4: Verify ZERO reference breaks and ZERO geometry resets!
assert.strictEqual(reader.bookshelf, initialBookshelfRef, "Bookshelf array reference MUST NOT change!");
assert.strictEqual(reader.bookshelf[0], initialBookRef, "Book object reference MUST NOT change!");
assert.strictEqual(reader.bookshelf[0].pages[0], initialPage1Ref, "Page 1 reference MUST NOT change!");
assert.strictEqual(reader.bookshelf[0].pages[1], initialPage2Ref, "Page 2 reference MUST NOT change!");

// Verify verified geometry remained locked
assert.strictEqual(initialPage1Ref.geometryVerified, true, "Page 1 geometryVerified must stay true!");
assert.strictEqual(initialPage1Ref.cardHeight, Math.round(474 * (1500 / 1000)), "Page 1 cardHeight must NOT be reset to 632!");
assert.strictEqual(initialPage1Ref.singleBaseWidth, 728, "Page 1 singleBaseWidth must stay 728px!");
assert.strictEqual(initialPage1Ref.hasThumb, true, "Page 1 thumb must be updated in place!");
assert.strictEqual(initialPage1Ref.thumbSrc, 'file:///path/01_thumb.jpg', "Page 1 thumbSrc must be updated!");

assert.strictEqual(initialPage2Ref.geometryVerified, true, "Page 2 geometryVerified must stay true!");
assert.strictEqual(initialPage2Ref.isWide, true, "Page 2 isWide must stay true!");
assert.strictEqual(initialPage2Ref.cardWidth, 950, "Page 2 cardWidth must stay 950px!");
assert.strictEqual(initialPage2Ref.singleBaseWidth, 972, "Page 2 singleBaseWidth must stay 972px!");

// Verify newly converted page was cleanly appended
assert.strictEqual(reader.bookshelf[0].pages.length, 3, "New page 3 must be appended!");
assert.strictEqual(reader.bookshelf[0].pages[2].fileName, '03.jpg', "Page 3 fileName matches!");
assert.strictEqual(reader.bookshelf[0].pages[2].id, 3, "Page 3 ID matches!");
assert.strictEqual(reader.bookshelf[0].webpDone, true, "webpDone updated!");
assert.strictEqual(reader.layoutVersion, 1, "layoutVersion incremented exactly once because a new page was appended!");

console.log("✓ Step 4: In-place patching verified with 100% precision!");
console.log("  - Array references preserved: YES");
console.log("  - Object references preserved: YES");
console.log("  - Verified geometry preserved: YES (NO RESET TO 474x632)");
console.log("  - Wide page format preserved: YES (NO SHRINK TO 728)");
console.log("  - Newly converted pages smoothly appended: YES");
console.log("ALL IN-PLACE PATCHING TESTS PASSED PERFECTLY!");
