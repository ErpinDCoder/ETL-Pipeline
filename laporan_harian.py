import sys
from datetime import date, datetime
from decimal import Decimal

import mysql.connector
from mysql.connector import Error
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QTableWidgetItem


DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "",
    "database": "db_datawarehouse_pembayaran",
}


class LaporanHarianWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("laporan_harian.ui", self)

        self.comboBulan.currentIndexChanged.connect(self.tampilkan_laporan)

        self.tableLaporan.setColumnWidth(0, 120)
        self.tableLaporan.setColumnWidth(1, 115)
        self.tableLaporan.setColumnWidth(2, 90)
        self.tableLaporan.setColumnWidth(3, 90)
        self.tableLaporan.setColumnWidth(4, 80)
        self.tableLaporan.setColumnWidth(5, 100)
        self.tableLaporan.setColumnWidth(6, 170)
        self.tableLaporan.setColumnWidth(7, 190)

        self.muat_bulan()

    def koneksi_db(self):
        """Membuka koneksi ke MariaDB."""
        return mysql.connector.connect(**DB_CONFIG)

    def muat_bulan(self, bulan_terpilih=None):
        """Memuat daftar bulan yang tersedia pada tabel ringkasan."""
        try:
            conn = self.koneksi_db()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT DATE_FORMAT(tanggal_pembayaran, '%Y-%m') AS bulan
                FROM mv_laporan_harian
                ORDER BY bulan
            """)
            bulan_list = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()

            self.comboBulan.blockSignals(True)
            self.comboBulan.clear()
            self.comboBulan.addItem("Semua Bulan", userData=None)

            for bulan in bulan_list:
                self.comboBulan.addItem(bulan, userData=bulan)

            if bulan_terpilih:
                index = self.comboBulan.findData(bulan_terpilih)
                if index >= 0:
                    self.comboBulan.setCurrentIndex(index)

            self.comboBulan.blockSignals(False)
            self.tampilkan_laporan()

        except Error as e:
            self.comboBulan.blockSignals(False)
            self.tampilkan_error(
                "Gagal mengambil daftar bulan.\n"
                "Pastikan database dan tabel mv_laporan_harian sudah dibuat.\n\n"
                f"Detail: {e}"
            )

    def tampilkan_laporan(self, *_):
        """Menampilkan laporan untuk bulan terpilih atau semua bulan."""
        bulan = self.comboBulan.currentData()

        try:
            conn = self.koneksi_db()
            cursor = conn.cursor()

            query = """
                SELECT
                    tanggal_pembayaran,
                    total_transaksi,
                    transaksi_berhasil,
                    transaksi_menunggu,
                    transaksi_gagal,
                    transaksi_dibatalkan,
                    nominal_total,
                    nominal_berhasil
                FROM mv_laporan_harian
            """
            params = ()

            if bulan:
                query += " WHERE DATE_FORMAT(tanggal_pembayaran, '%Y-%m') = %s"
                params = (bulan,)

            query += " ORDER BY tanggal_pembayaran"

            cursor.execute(query, params)
            rows = cursor.fetchall()
            cursor.close()
            conn.close()

            self.tableLaporan.setSortingEnabled(False)
            self.tableLaporan.setRowCount(0)

            for row_data in rows:
                row_index = self.tableLaporan.rowCount()
                self.tableLaporan.insertRow(row_index)

                for col_index, value in enumerate(row_data):
                    if isinstance(value, (Decimal, float)):
                        text = f"{value:,.2f}"
                    elif isinstance(value, (date, datetime)):
                        text = value.strftime("%Y-%m-%d")
                    else:
                        text = str(value if value is not None else "")

                    item = QTableWidgetItem(text)
                    if col_index >= 6:
                        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.tableLaporan.setItem(row_index, col_index, item)

            self.tableLaporan.setSortingEnabled(True)
            self.labelStatus.setText(
                f"Menampilkan {len(rows)} hari transaksi"
                + (f" untuk bulan {bulan}." if bulan else " dari semua bulan.")
            )

        except Error as e:
            self.tampilkan_error(f"Gagal menampilkan laporan.\n\nDetail: {e}")

    def tampilkan_error(self, pesan):
        self.labelStatus.setText("Terjadi kesalahan.")
        QMessageBox.critical(self, "Kesalahan Database", pesan)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LaporanHarianWindow()
    window.show()
    sys.exit(app.exec_())
