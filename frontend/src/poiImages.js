// Curated images only: never reuse one landmark's photograph for another POI.
import catalogueImages from "./poiImages.generated.json";

export const poiImages = {
  ...catalogueImages,
  hn_001: {
    src: "/images/pois/van-mieu.jpg",
    alt: "Khuê Văn Các tại Văn Miếu – Quốc Tử Giám, Hà Nội",
    author: "Chuoibk",
    source:
      "https://commons.wikimedia.org/wiki/File:Khu%C3%AA_V%C4%83n_Pavillion_cropped.jpg",
    license: "CC BY-SA 4.0",
    licenseUrl: "https://creativecommons.org/licenses/by-sa/4.0/",
  },
};
