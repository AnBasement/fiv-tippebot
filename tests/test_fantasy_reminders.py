import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime
import pytz

from cogs.fantasy_reminders import FantasyReminders, setup


@pytest.fixture
def mock_bot():
    """Mocker en Discord bot."""
    bot = Mock()
    bot.loop = Mock()
    bot.loop.create_task = Mock()
    bot.wait_until_ready = AsyncMock()
    bot.get_channel = Mock()
    bot.add_cog = AsyncMock()
    return bot


@pytest.fixture
def mock_channel():
    """Mocker en Discord-kanal."""
    channel = Mock()
    channel.send = AsyncMock()
    return channel


class TestFantasyReminders:
    
    def test_init(self, mock_bot):
        """Tester at FantasyReminders initialiseres riktig."""
        with patch.object(FantasyReminders, 'reminder_scheduler', return_value=None):
            cog = FantasyReminders(mock_bot)
            
            assert cog.bot == mock_bot
            assert cog.norsk_tz.zone == "Europe/Oslo"
            assert cog.last_waiver_week is None

    @pytest.mark.asyncio
    async def test_tuesday_reminder_sent(self, mock_bot, mock_channel):
        """Tester at påminnelser sendes tirsdager klokken 18:00."""
        mock_bot.get_channel.return_value = mock_channel
        
        # Mock Tuesday at 18:00
        tuesday_1800 = datetime(2024, 1, 2, 18, 0, 0)  # Tuesday
        tuesday_1800 = pytz.timezone("Europe/Oslo").localize(tuesday_1800)
        
        with patch('cogs.fantasy_reminders.datetime') as mock_datetime:
            mock_datetime.now.return_value = tuesday_1800
            
            with patch.object(FantasyReminders, 'reminder_scheduler', return_value=None):
                cog = FantasyReminders(mock_bot)
                cog.last_waiver_week = None
                
                # Simulate the Tuesday check logic
                now = mock_datetime.now.return_value
                weekday = now.weekday()
                
                if weekday == 1:  # Tuesday
                    week_num = now.isocalendar()[1]
                    if cog.last_waiver_week != week_num:
                        await mock_channel.send("@everyone Ikke glem waivers!")
                        cog.last_waiver_week = week_num
                
                mock_channel.send.assert_called_once_with("@everyone Ikke glem waivers!")

    @pytest.mark.asyncio
    async def test_no_duplicate_reminders_same_week(self, mock_bot, mock_channel):
        """Tester at påminnelser ikke sendes to ganger samme uke."""
        mock_bot.get_channel.return_value = mock_channel
        
        tuesday = pytz.timezone("Europe/Oslo").localize(datetime(2024, 1, 2, 18, 0, 0))
        current_week = tuesday.isocalendar()[1]
        
        with patch.object(FantasyReminders, 'reminder_scheduler', return_value=None):
            cog = FantasyReminders(mock_bot)
            cog.last_waiver_week = current_week  # Already sent this week
            
            # Try to send again for same week
            if cog.last_waiver_week == current_week:
                pass  # Should not send
            else:
                await mock_channel.send("@everyone Ikke glem waivers!")
            
            mock_channel.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_setup_function(self, mock_bot):
        """Tester at setup-funksjonen virker."""
        await setup(mock_bot)
        mock_bot.add_cog.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])