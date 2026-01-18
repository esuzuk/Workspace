
package com.example.calendarwidget.widget

import android.content.Context
import androidx.compose.runtime.Composable
import androidx.glance.appwidget.GlanceAppWidget
import androidx.glance.appwidget.GlanceAppWidgetReceiver
import androidx.glance.appwidget.provideContent

class CalendarWidget : GlanceAppWidget() {

    override suspend fun provideGlance(context: Context, id: androidx.glance.GlanceId) {
        provideContent {
            CalendarWidgetContent()
        }
    }

    @Composable
    private fun CalendarWidgetContent() {
        // TODO: Implement calendar UI
    }
}

class CalendarWidgetReceiver : GlanceAppWidgetReceiver() {
    override val glanceAppWidget: GlanceAppWidget = CalendarWidget()
}
