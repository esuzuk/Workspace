
package com.example.calendarwidget.data

import android.content.Context
import java.time.LocalDate
import java.time.format.DateTimeFormatter

class HolidayRepository(private val context: Context) {

    fun getHolidays(): List<Holiday> {
        val holidays = mutableListOf<Holiday>()
        val csvStream = context.assets.open("holidays.csv")
        csvStream.bufferedReader().useLines {
            lines ->
            lines.drop(1).forEach {
                val tokens = it.split(",")
                val date = LocalDate.parse(tokens[0], DateTimeFormatter.ofPattern("yyyy/M/d"))
                holidays.add(Holiday(date, tokens[1]))
            }
        }
        return holidays
    }
}
