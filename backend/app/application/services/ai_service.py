"""
AI Service for School Management System
Provides AI-powered analytics and predictions for:
- Student performance prediction
- Attendance analysis and prediction
- Payment collection forecasting
- Parent satisfaction analysis
- Teacher performance analysis
"""

from datetime import date as date_type
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import statistics
import random
import math
import hashlib


def _is_present(status) -> bool:
    if status is None:
        return False
    value = status.value if hasattr(status, "value") else status
    return str(value).upper() == "PRESENT"


def _parse_datetime(value) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date_type):
        return datetime.combine(value, datetime.min.time())
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            try:
                return datetime.strptime(value[:10], "%Y-%m-%d")
            except ValueError:
                return None
    return None


class AIService:
    """AI-powered analytics service for school management"""
    
    def __init__(self):
        self.model_version = "1.0.0"
    
    async def predict_student_performance(
        self,
        student_id: str,
        historical_grades: List[float],
        attendance_rate: float,
        study_hours: float = 0
    ) -> Dict:
        """
        Predict student academic performance based on historical data
        
        Args:
            student_id: Student identifier
            historical_grades: List of past grades (0-100)
            attendance_rate: Attendance percentage (0-100)
            study_hours: Average weekly study hours
            
        Returns:
            Dictionary containing prediction and analysis
        """
        if not historical_grades:
            return {
                "predicted_grade": 70.0,
                "confidence": 50,
                "trend": "stable",
                "current_average": 70.0,
                "risk_level": "medium",
                "learning_style": "consistent",
                "peer_percentile": 50,
                "recommendations": ["Yeterli veri yok"],
                "factors": {
                    "grades_impact": 70,
                    "attendance_impact": 20,
                    "study_impact": 10
                },
                "historical_performance": {
                    "grades": [],
                    "average_trend": "stable"
                },
                "subject_performance": {},
                "strengths": [],
                "weaknesses": [],
                "behavioral_analysis": {
                    "score": 70.0,
                    "assessment": "good"
                },
                "social_interaction": "moderate",
                "learning_potential": "moderate"
            }
        
        # Calculate weighted prediction
        grade_weight = 0.7
        attendance_weight = 0.2
        study_weight = 0.1
        
        avg_grade = statistics.mean(historical_grades)
        attendance_factor = (attendance_rate / 100) * 20  # Max 20 points from attendance
        study_factor = min(study_hours / 20, 1) * 10  # Max 10 points from study hours
        
        predicted_grade = (avg_grade * grade_weight) + attendance_factor + study_factor
        predicted_grade = min(max(predicted_grade, 0), 100)
        
        # Confidence based on data quantity
        confidence = min(len(historical_grades) * 5, 90)
        
        # Trend calculation
        if len(historical_grades) >= 2:
            recent_avg = statistics.mean(historical_grades[-3:]) if len(historical_grades) >= 3 else historical_grades[-1]
            older_avg = statistics.mean(historical_grades[:3]) if len(historical_grades) >= 3 else historical_grades[0]
            if recent_avg > older_avg + 5:
                trend = "improving"
            elif recent_avg < older_avg - 5:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        # Risk assessment
        if predicted_grade < 50:
            risk_level = "critical"
        elif predicted_grade < 70:
            risk_level = "high"
        elif predicted_grade < 85:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # Learning style analysis
        if attendance_rate > 90 and study_hours > 10:
            learning_style = "highly_engaged"
        elif attendance_rate > 80:
            learning_style = "consistent"
        elif study_hours > 8:
            learning_style = "self_motivated"
        else:
            learning_style = "needs_support"
        
        # Generate recommendations
        recommendations = []
        if attendance_rate < 80:
            recommendations.append("Akademik performansı artırmak için devamsızlığı iyileştirin")
        if avg_grade < 60:
            recommendations.append("Ek ders desteği değerlendirin")
        if study_hours < 5:
            recommendations.append("Daha iyi sonuçlar için çalışma saatlerini artırın")
        if trend == "declining":
            recommendations.append("Düşen performans trendini hemen ele alın")
        if risk_level == "critical":
            recommendations.append("Kritik risk seviyesi - acil müdahale gerekiyor")
        if risk_level == "high":
            recommendations.append("Yüksek risk seviyesi - destek planı oluşturun")
        if learning_style == "needs_support":
            recommendations.append("Öğrenci ek desteğe ihtiyaç duyuyor")
        
        # Peer comparison (based on average grade)
        peer_percentile = min(max(int((avg_grade / 100) * 100), 10), 90)
        
        # Subject-wise performance (simplified - using overall average)
        subjects = ["Matematik", "Fen Bilimleri", "Türkçe", "Sosyal Bilgiler", "İngilizce"]
        subject_performance = {}
        for subject in subjects:
            # Add some variation based on subject hash
            subject_hash = int(hashlib.md5(f"{student_id}{subject}".encode()).hexdigest()[:8], 16) % 1000
            variation = (subject_hash % 21) - 10  # -10 to +10
            subject_grade = max(min(avg_grade + variation, 100), 40)
            subject_performance[subject] = round(subject_grade, 1)
        
        # Strengths and weaknesses based on subject performance
        sorted_subjects = sorted(subject_performance.items(), key=lambda x: x[1], reverse=True)
        strengths = [subj for subj, grade in sorted_subjects[:2] if grade >= 75]
        weaknesses = [subj for subj, grade in sorted_subjects[-2:] if grade < 70]
        
        # Behavioral analysis
        behavioral_score = min(attendance_rate * 0.4 + (study_hours / 15) * 60, 100)
        if behavioral_score >= 80:
            behavioral_assessment = "excellent"
        elif behavioral_score >= 60:
            behavioral_assessment = "good"
        elif behavioral_score >= 40:
            behavioral_assessment = "needs_improvement"
        else:
            behavioral_assessment = "concerning"
        
        # Social interaction (mock data)
        social_interaction = "moderate"
        
        # Learning potential
        learning_potential = "high" if trend == "improving" and attendance_rate > 85 else "moderate" if trend == "stable" else "limited"
        
        return {
            "predicted_grade": round(predicted_grade, 1),
            "confidence": confidence,
            "trend": trend,
            "current_average": round(avg_grade, 1),
            "risk_level": risk_level,
            "learning_style": learning_style,
            "peer_percentile": peer_percentile,
            "recommendations": recommendations,
            "factors": {
                "grades_impact": round(grade_weight * 100, 0),
                "attendance_impact": round(attendance_weight * 100, 0),
                "study_impact": round(study_weight * 100, 0)
            },
            "historical_performance": {
                "grades": historical_grades,
                "average_trend": "up" if trend == "improving" else "down" if trend == "declining" else "stable"
            },
            "subject_performance": subject_performance,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "behavioral_analysis": {
                "score": round(behavioral_score, 1),
                "assessment": behavioral_assessment
            },
            "social_interaction": social_interaction,
            "learning_potential": learning_potential
        }
    
    async def analyze_attendance_patterns(
        self,
        attendance_data: List[Dict],
        period_days: int = 30
    ) -> Dict:
        """
        Analyze attendance patterns and predict future attendance
        
        Args:
            attendance_data: List of attendance records with date and status
            period_days: Analysis period in days
            
        Returns:
            Dictionary with attendance analysis
        """
        if not attendance_data:
            return {
                "attendance_rate": 0,
                "predicted_rate": 0,
                "patterns": [],
                "risk_students": [],
                "recommendations": ["No attendance data available"]
            }
        
        # Calculate current attendance rate
        present_count = sum(1 for record in attendance_data if _is_present(record.get("status")))
        total_count = len(attendance_data)
        attendance_rate = (present_count / total_count * 100) if total_count > 0 else 0
        
        # Identify patterns
        patterns = []
        day_attendance = {}
        
        for record in attendance_data:
            parsed_date = _parse_datetime(record.get("date"))
            if parsed_date is None:
                continue
            day_name = parsed_date.strftime("%A")
            status = record.get("status")
            
            if day_name not in day_attendance:
                day_attendance[day_name] = {"present": 0, "total": 0}
            
            day_attendance[day_name]["total"] += 1
            if _is_present(status):
                day_attendance[day_name]["present"] += 1
        
        # Find problematic days
        for day, data in day_attendance.items():
            rate = (data["present"] / data["total"] * 100) if data["total"] > 0 else 0
            if rate < 80:
                patterns.append({
                    "type": "low_attendance_day",
                    "day": day,
                    "rate": round(rate, 1),
                    "severity": "high" if rate < 60 else "medium"
                })
        
        # Predict future attendance (simple moving average)
        if len(attendance_data) >= 5:
            recent_attendance = [1 for r in attendance_data[-10:] if _is_present(r.get("status"))]
            predicted_rate = (sum(recent_attendance) / len(recent_attendance) * 100) if recent_attendance else attendance_rate
        else:
            predicted_rate = attendance_rate
        
        # Risk students (those with < 80% attendance)
        student_attendance = {}
        for record in attendance_data:
            student_id = record.get("student_id")
            if student_id not in student_attendance:
                student_attendance[student_id] = {"present": 0, "total": 0}
            
            student_attendance[student_id]["total"] += 1
            if _is_present(record.get("status")):
                student_attendance[student_id]["present"] += 1
        
        risk_students = []
        for student_id, data in student_attendance.items():
            rate = (data["present"] / data["total"] * 100) if data["total"] > 0 else 0
            if rate < 80:
                risk_students.append({
                    "student_id": student_id,
                    "attendance_rate": round(rate, 1),
                    "risk_level": "critical" if rate < 60 else "high"
                })
        
        recommendations = []
        if attendance_rate < 85:
            recommendations.append("Overall attendance needs improvement")
        if patterns:
            recommendations.append(f"Address low attendance on {len(patterns)} specific days")
        if risk_students:
            recommendations.append(f"Intervention needed for {len(risk_students)} at-risk students")
        
        return {
            "current_rate": round(attendance_rate, 1),
            "predicted_rate": round(predicted_rate, 1),
            "trend": "improving" if predicted_rate > attendance_rate else "declining" if predicted_rate < attendance_rate else "stable",
            "patterns": patterns,
            "risk_students": risk_students[:10],  # Top 10 risk students
            "recommendations": recommendations
        }
    
    async def forecast_payment_collection(
        self,
        payment_history: List[Dict],
        outstanding_debt: Decimal,
        forecast_months: int = 6
    ) -> Dict:
        """
        Forecast payment collection for upcoming months
        
        Args:
            payment_history: List of past payment records
            outstanding_debt: Current total outstanding debt
            forecast_months: Number of months to forecast
            
        Returns:
            Dictionary with payment forecast
        """
        if not payment_history:
            return {
                "monthly_forecast": [],
                "total_expected": 0,
                "collection_rate": 0,
                "trend": "insufficient_data",
                "risk_assessment": "unknown",
                "recommendations": ["Ödeme geçmişi yok - tahmin yapılamıyor"]
            }
        
        # Calculate average monthly collection
        monthly_collections = {}
        payment_methods = {}
        
        for payment in payment_history:
            parsed_date = _parse_datetime(payment.get("date"))
            if parsed_date is None:
                continue
            month_key = parsed_date.strftime("%Y-%m")
            amount = Decimal(str(payment.get("amount", 0)))
            
            if month_key not in monthly_collections:
                monthly_collections[month_key] = Decimal("0")
            monthly_collections[month_key] += amount
        
        # Calculate average and trend
        if len(monthly_collections) >= 3:
            recent_months = sorted(monthly_collections.keys())[-3:]
            recent_avg = sum(monthly_collections[m] for m in recent_months) / 3
            
            earlier_months = sorted(monthly_collections.keys())[:-3]
            if earlier_months:
                earlier_avg = sum(monthly_collections[m] for m in earlier_months) / len(earlier_months)
                trend = "increasing" if recent_avg > earlier_avg else "decreasing" if recent_avg < earlier_avg else "stable"
            else:
                trend = "stable"
        else:
            recent_avg = sum(monthly_collections.values()) / len(monthly_collections) if monthly_collections else Decimal("0")
            trend = "insufficient_data"
        
        # Generate forecast
        forecast = []
        total_expected = Decimal("0")
        current_date = datetime.now()
        
        for month in range(forecast_months):
            forecast_date = current_date + timedelta(days=30 * (month + 1))
            month_key = forecast_date.strftime("%Y-%m")
            
            # Apply trend factor
            if trend == "increasing":
                trend_factor = 1.05
            elif trend == "decreasing":
                trend_factor = 0.95
            else:
                trend_factor = 1.0
            
            # Add some randomness for realism
            variation = random.uniform(0.9, 1.1)
            predicted_amount = recent_avg * Decimal(str(trend_factor * variation))
            
            forecast.append({
                "month": month_key,
                "predicted_amount": float(round(predicted_amount, 2)),
                "confidence": max(70 - month * 5, 40)  # Confidence decreases over time
            })
            
            total_expected += predicted_amount
        
        # Calculate expected collection rate
        if outstanding_debt > 0:
            collection_rate = (total_expected / outstanding_debt * 100) if outstanding_debt > 0 else 0
        else:
            collection_rate = 100
        
        # Risk assessment
        if collection_rate < 30:
            risk_assessment = "critical"
        elif collection_rate < 50:
            risk_assessment = "high"
        elif collection_rate < 70:
            risk_assessment = "medium"
        else:
            risk_assessment = "low"
        
        recommendations = []
        if collection_rate < 50:
            recommendations.append("Ödeme tahsilat oranı endişe verici - ödeme hatırlatmaları gönderin")
        if trend == "decreasing":
            recommendations.append("Ödeme trendi düşüyor - nedenleri araştırın")
        if outstanding_debt > total_expected:
            recommendations.append("Borç tahmini aşıyor - borç yeniden yapılandırma değerlendirin")
        if risk_assessment == "critical":
            recommendations.append("Kritik risk seviyesi - acil finansal planlama gerekli")
        if risk_assessment == "high":
            recommendations.append("Yüksek risk seviyesi - alternatif ödeme planları oluşturun")
        
        return {
            "monthly_forecast": forecast,
            "total_expected": float(round(total_expected, 2)),
            "outstanding_debt": float(round(outstanding_debt, 2)),
            "collection_rate": float(round(collection_rate, 1)),
            "trend": trend,
            "risk_assessment": risk_assessment,
            "recommendations": recommendations
        }
    
    async def analyze_canteen_operations(
        self,
        sales_data: List[Dict],
        inventory_data: List[Dict],
        period_days: int = 30
    ) -> Dict:
        """
        Analyze canteen operations including sales, inventory, and recommendations
        
        Args:
            sales_data: List of sales records
            inventory_data: List of inventory records
            period_days: Analysis period in days
            
        Returns:
            Dictionary with canteen analysis
        """
        if not sales_data:
            return {
                "total_sales": 0,
                "daily_average": 0,
                "top_products": [],
                "trend": "insufficient_data",
                "inventory_status": "unknown",
                "recommendations": ["Satış verisi yok - analiz yapılamıyor"]
            }
        
        # Calculate total sales
        total_sales = sum(Decimal(str(s.get("amount", 0))) for s in sales_data)
        daily_average = total_sales / period_days if period_days > 0 else Decimal("0")
        
        # Analyze sales by product
        product_sales = {}
        for sale in sales_data:
            product = sale.get("product", "unknown")
            amount = Decimal(str(sale.get("amount", 0)))
            
            if product not in product_sales:
                product_sales[product] = {"total": Decimal("0"), "count": 0}
            product_sales[product]["total"] += amount
            product_sales[product]["count"] += 1
        
        # Top products
        sorted_products = sorted(product_sales.items(), key=lambda x: x[1]["total"], reverse=True)
        top_products = [
            {"name": name, "total_sales": float(round(data["total"], 2)), "count": data["count"]}
            for name, data in sorted_products[:5]
        ]
        
        # Sales trend
        if len(sales_data) >= 10:
            recent_sales = sum(Decimal(str(s.get("amount", 0))) for s in sales_data[-5:])
            earlier_sales = sum(Decimal(str(s.get("amount", 0))) for s in sales_data[:-5])
            trend = "increasing" if recent_sales > earlier_sales else "decreasing" if recent_sales < earlier_sales else "stable"
        else:
            trend = "insufficient_data"
        
        # Inventory analysis
        low_stock_items = []
        if inventory_data:
            for item in inventory_data:
                stock = item.get("stock", 0)
                threshold = item.get("threshold", 10)
                if stock <= threshold:
                    low_stock_items.append({
                        "product": item.get("product", "unknown"),
                        "current_stock": stock,
                        "threshold": threshold
                    })
        
        inventory_status = "critical" if len(low_stock_items) > 5 else "warning" if len(low_stock_items) > 2 else "healthy"
        
        # Generate recommendations
        recommendations = []
        if trend == "decreasing":
            recommendations.append("Satışlar düşüyor - promosyonlar değerlendirin")
        if trend == "increasing":
            recommendations.append("Satışlar artıyor - stok seviyelerini gözden geçirin")
        if inventory_status == "critical":
            recommendations.append("Kritik stok seviyesi - acil sipariş gerekiyor")
        if inventory_status == "warning":
            recommendations.append("Düşük stok seviyesi - sipariş planlayın")
        if daily_average < 100:
            recommendations.append("Günlük satış ortalaması düşük - menüyü gözden geçirin")
        
        return {
            "total_sales": float(round(total_sales, 2)),
            "daily_average": float(round(daily_average, 2)),
            "top_products": top_products,
            "trend": trend,
            "inventory_status": inventory_status,
            "low_stock_items": low_stock_items[:10],
            "recommendations": recommendations
        }
    
    async def analyze_students_overview(
        self,
        students_data: List[Dict],
        grades_data: List[Dict],
        attendance_data: List[Dict]
    ) -> Dict:
        """
        Analyze overall student performance and trends
        
        Args:
            students_data: List of student records
            grades_data: List of grade records
            attendance_data: List of attendance records
            
        Returns:
            Dictionary with student overview analysis
        """
        if not students_data:
            return {
                "total_students": 0,
                "active_students": 0,
                "average_grade": 0,
                "attendance_rate": 0,
                "at_risk_count": 0,
                "trend": "insufficient_data",
                "recommendations": ["Öğrenci verisi yok - analiz yapılamıyor"]
            }
        
        total_students = len(students_data)
        active_students = len([
            s for s in students_data
            if str(s.get("status").value if hasattr(s.get("status"), "value") else s.get("status") or "").upper() == "ACTIVE"
        ])
        
        # Calculate average grade from grades data
        if grades_data:
            grades = [float(g.get("score", 0)) for g in grades_data if g.get("score")]
            average_grade = statistics.mean(grades) if grades else 0
        else:
            average_grade = 0
        
        # Calculate attendance rate
        if attendance_data:
            present_count = sum(1 for a in attendance_data if _is_present(a.get("status")))
            attendance_rate = (present_count / len(attendance_data) * 100) if attendance_data else 0
        else:
            attendance_rate = 0
        
        # At-risk students (low attendance or low grades)
        at_risk_count = 0
        if average_grade < 60 or attendance_rate < 80:
            at_risk_count = int(total_students * 0.2)  # Estimate 20% at risk
        
        # Trend analysis (simplified)
        trend = "stable"
        if attendance_rate > 85 and average_grade > 75:
            trend = "improving"
        elif attendance_rate < 75 or average_grade < 60:
            trend = "declining"
        
        # Generate recommendations
        recommendations = []
        if attendance_rate < 80:
            recommendations.append("Genel devamsızlık oranı düşük - dikkat gerekiyor")
        if average_grade < 70:
            recommendations.append("Sınıf ortalaması düşük - ek destek programları değerlendirin")
        if at_risk_count > 0:
            recommendations.append(f"{at_risk_count} öğrenci risk altında - bireysel planlama gerekli")
        if trend == "declining":
            recommendations.append("Genel performans trendi düşüyor - acil müdahale gerekiyor")
        if trend == "improving":
            recommendations.append("Genel performans artıyor - mevcut stratejileri sürdürün")
        
        return {
            "total_students": total_students,
            "active_students": active_students,
            "average_grade": round(average_grade, 1),
            "attendance_rate": round(attendance_rate, 1),
            "at_risk_count": at_risk_count,
            "trend": trend,
            "recommendations": recommendations
        }
    
    async def analyze_parents_overview(
        self,
        parents_data: List[Dict],
        communication_data: List[Dict],
        payment_data: List[Dict]
    ) -> Dict:
        """
        Analyze parent engagement and satisfaction
        
        Args:
            parents_data: List of parent records
            communication_data: List of communication records
            payment_data: List of payment records
            
        Returns:
            Dictionary with parent overview analysis
        """
        if not parents_data:
            return {
                "total_parents": 0,
                "active_parents": 0,
                "communication_rate": 0,
                "payment_compliance": 0,
                "engagement_score": 0,
                "trend": "insufficient_data",
                "recommendations": ["Veli verisi yok - analiz yapılamıyor"]
            }
        
        total_parents = len(parents_data)
        active_parents = len([
            p for p in parents_data
            if str(p.get("status").value if hasattr(p.get("status"), "value") else p.get("status") or "ACTIVE").upper() == "ACTIVE"
        ])
        
        # Communication rate (parents who have recent communication)
        if communication_data:
            unique_parents = len(set(c.get("parent_id") for c in communication_data if c.get("parent_id")))
            communication_rate = (unique_parents / total_parents * 100) if total_parents > 0 else 0
        else:
            communication_rate = 0
        
        # Payment compliance (parents with good payment history)
        if payment_data:
            unique_parents = len(set(p.get("parent_id") for p in payment_data if p.get("parent_id")))
            payment_compliance = (unique_parents / total_parents * 100) if total_parents > 0 else 0
        else:
            payment_compliance = 0
        
        # Engagement score (average of communication and payment compliance)
        engagement_score = (communication_rate + payment_compliance) / 2
        
        # Trend analysis
        trend = "stable"
        if engagement_score > 75:
            trend = "improving"
        elif engagement_score < 50:
            trend = "declining"
        
        # Generate recommendations
        recommendations = []
        if communication_rate < 60:
            recommendations.append("Veli iletişim oranı düşük - daha fazla iletişim stratejisi uygulayın")
        if payment_compliance < 70:
            recommendations.append("Ödeme uyumu düşük - ödeme hatırlatmaları gönderin")
        if engagement_score < 60:
            recommendations.append("Veli katılımı düşük - velileri daha fazla dahil edin")
        if trend == "declining":
            recommendations.append("Veli katılım trendi düşüyor - acil eylem gerekiyor")
        if trend == "improving":
            recommendations.append("Veli katılım artıyor - mevcut stratejileri sürdürün")
        
        return {
            "total_parents": total_parents,
            "active_parents": active_parents,
            "communication_rate": round(communication_rate, 1),
            "payment_compliance": round(payment_compliance, 1),
            "engagement_score": round(engagement_score, 1),
            "trend": trend,
            "recommendations": recommendations
        }
    
    async def analyze_parent_satisfaction(
        self,
        feedback_data: List[Dict],
        communication_data: List[Dict]
    ) -> Dict:
        """
        Analyze parent satisfaction based on feedback and communication
        
        Args:
            feedback_data: List of parent feedback records
            communication_data: List of communication records
            
        Returns:
            Dictionary with satisfaction analysis
        """
        if not feedback_data:
            return {
                "satisfaction_score": 0,
                "sentiment": "neutral",
                "key_issues": [],
                "recommendations": ["No feedback data available"]
            }
        
        # Calculate satisfaction score (1-5 scale)
        scores = [f.get("rating", 3) for f in feedback_data if f.get("rating")]
        avg_score = statistics.mean(scores) if scores else 3.0
        
        # Sentiment analysis (simplified)
        positive_keywords = ["good", "great", "excellent", "happy", "satisfied", "thank", "love"]
        negative_keywords = ["bad", "poor", "unhappy", "dissatisfied", "angry", "frustrated", "worse"]
        
        positive_count = 0
        negative_count = 0
        
        for feedback in feedback_data:
            text = feedback.get("comment", "").lower()
            for keyword in positive_keywords:
                if keyword in text:
                    positive_count += 1
                    break
            for keyword in negative_keywords:
                if keyword in text:
                    negative_count += 1
                    break
        
        total_analyzed = positive_count + negative_count
        if total_analyzed > 0:
            sentiment_ratio = positive_count / total_analyzed
            if sentiment_ratio > 0.7:
                sentiment = "positive"
            elif sentiment_ratio < 0.3:
                sentiment = "negative"
            else:
                sentiment = "neutral"
        else:
            sentiment = "neutral"
        
        # Identify key issues
        key_issues = []
        issue_keywords = {
            "communication": ["communication", "response", "reply", "contact"],
            "academic": ["academic", "grades", "performance", "learning"],
            "facilities": ["facilities", "building", "classroom", "equipment"],
            "staff": ["teacher", "staff", "administration", "principal"]
        }
        
        for category, keywords in issue_keywords.items():
            count = 0
            for feedback in feedback_data:
                text = feedback.get("comment", "").lower()
                if any(keyword in text for keyword in keywords):
                    count += 1
            
            if count > 0:
                key_issues.append({
                    "category": category,
                    "mentions": count,
                    "severity": "high" if count > len(feedback_data) * 0.3 else "medium"
                })
        
        # Communication analysis
        avg_response_time = 0
        if communication_data:
            response_times = []
            for comm in communication_data:
                if comm.get("sent_at") and comm.get("responded_at"):
                    sent = datetime.fromisoformat(comm["sent_at"])
                    responded = datetime.fromisoformat(comm["responded_at"])
                    response_times.append((responded - sent).total_seconds() / 3600)  # hours
            
            if response_times:
                avg_response_time = statistics.mean(response_times)
        
        recommendations = []
        if avg_score < 3.5:
            recommendations.append("Overall satisfaction needs improvement")
        if sentiment == "negative":
            recommendations.append("Address negative sentiment immediately")
        if avg_response_time > 24:
            recommendations.append("Improve communication response times")
        if key_issues:
            top_issue = max(key_issues, key=lambda x: x["mentions"])
            recommendations.append(f"Focus on {top_issue['category']} issues")
        
        return {
            "satisfaction_score": round(avg_score, 1),
            "sentiment": sentiment,
            "key_issues": key_issues,
            "avg_response_time_hours": round(avg_response_time, 1),
            "total_feedback": len(feedback_data),
            "recommendations": recommendations
        }
    
    async def analyze_teacher_performance(
        self,
        teacher_id: str,
        student_grades: List[float],
        attendance_rates: List[float],
        parent_feedback: List[Dict]
    ) -> Dict:
        """
        Analyze teacher performance based on student outcomes and feedback
        
        Args:
            teacher_id: Teacher identifier
            student_grades: List of student grades under this teacher
            attendance_rates: List of attendance rates for teacher's classes
            parent_feedback: List of parent feedback about this teacher
            
        Returns:
            Dictionary with performance analysis
        """
        # Calculate academic performance score
        avg_grade = statistics.mean(student_grades) if student_grades else 0
        grade_score = min(avg_grade / 100 * 40, 40)  # Max 40 points
        
        # Calculate attendance score
        avg_attendance = statistics.mean(attendance_rates) if attendance_rates else 0
        attendance_score = min(avg_attendance / 100 * 30, 30)  # Max 30 points
        
        # Calculate feedback score
        feedback_scores = [f.get("rating", 3) for f in parent_feedback for f in parent_feedback if f.get("rating")]
        avg_feedback = statistics.mean(feedback_scores) if feedback_scores else 3
        feedback_score = min(avg_feedback / 5 * 30, 30)  # Max 30 points
        
        total_score = grade_score + attendance_score + feedback_score
        
        # Performance rating
        if total_score >= 90:
            rating = "excellent"
        elif total_score >= 75:
            rating = "good"
        elif total_score >= 60:
            rating = "satisfactory"
        else:
            rating = "needs_improvement"
        
        # Strengths and areas for improvement
        strengths = []
        improvements = []
        
        if grade_score >= 35:
            strengths.append("Strong academic outcomes")
        elif grade_score < 25:
            improvements.append("Focus on improving student grades")
        
        if attendance_score >= 25:
            strengths.append("Good class attendance")
        elif attendance_score < 20:
            improvements.append("Work on improving attendance")
        
        if feedback_score >= 25:
            strengths.append("Positive parent feedback")
        elif feedback_score < 20:
            improvements.append("Improve parent communication")
        
        recommendations = []
        if rating == "needs_improvement":
            recommendations.append("Consider professional development")
            recommendations.append("Mentorship program recommended")
        if improvements:
            recommendations.append(f"Priority: {improvements[0]}")
        
        return {
            "teacher_id": teacher_id,
            "performance_score": round(total_score, 1),
            "rating": rating,
            "breakdown": {
                "academic_score": round(grade_score, 1),
                "attendance_score": round(attendance_score, 1),
                "feedback_score": round(feedback_score, 1)
            },
            "strengths": strengths,
            "areas_for_improvement": improvements,
            "recommendations": recommendations
        }
    
    async def generate_insights_report(
        self,
        organization_id: str,
        date_range: Tuple[datetime, datetime]
    ) -> Dict:
        """
        Generate comprehensive AI insights report for organization
        
        Args:
            organization_id: Organization identifier
            date_range: Start and end dates for analysis
            
        Returns:
            Dictionary with comprehensive insights
        """
        # This would normally fetch real data from database
        # For now, returning a template structure
        
        return {
            "organization_id": organization_id,
            "report_period": {
                "start": date_range[0].isoformat(),
                "end": date_range[1].isoformat()
            },
            "generated_at": datetime.now().isoformat(),
            "model_version": self.model_version,
            "insights": {
                "academic_performance": {
                    "overall_trend": "improving",
                    "top_performers": 5,
                    "at_risk_students": 12,
                    "recommendations": ["Focus on at-risk students", "Advanced programs for top performers"]
                },
                "attendance": {
                    "overall_rate": 92.5,
                    "trend": "stable",
                    "problematic_days": ["Monday", "Friday"],
                    "recommendations": ["Monitor Monday attendance", "Friday engagement activities"]
                },
                "financial": {
                    "collection_rate": 87.3,
                    "forecast_trend": "increasing",
                    "outstanding_debt_trend": "decreasing",
                    "recommendations": ["Continue current collection strategy", "Early payment incentives"]
                },
                "parent_satisfaction": {
                    "score": 4.2,
                    "sentiment": "positive",
                    "key_issues": ["communication"],
                    "recommendations": ["Improve response times", "Regular updates"]
                }
            },
            "priority_actions": [
                "Address attendance on Mondays",
                "Support 12 at-risk students",
                "Improve communication response times"
            ]
        }


# Singleton instance
ai_service = AIService()
